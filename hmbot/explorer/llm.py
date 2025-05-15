import json
import re
import threading
import time
# import cv2
from loguru import logger
from openai import OpenAI
from .explorer import Explorer
from .prompt import *
from ..cv import _crop, encode_image
from ..event import *
from ..proto import SwipeDirection, ExploreGoal, AudioStatus, ResourceType, AudioType
from ..wtg import WTG, WTGParser


class LLM(Explorer):
    def __init__(self, device=None, app=None, url='', model='', api_key=''):
        super().__init__(device, app)
        self.client = OpenAI(api_key=api_key, base_url=url)
        self.model = model
        self.terminated = False
        self.lock = threading.Lock()
        self.close = False
        self.wtg = WTG()
        self.events = []
        self.ability_count = set()
        self.edges_count = 0

    def _ask(self, prompt, retry=3):
        """
        Get response from LLM
        """
        while retry > 0:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert in mobile phone operations."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=False,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(e)
                retry -= 1

    def explore(self, **goal):
        start = time.time()
        # Start a thread to check if the audio is turned on
        t1 = threading.Thread(target=self._should_terminate_thread, args=(goal,))
        t1.start()
        time.sleep(2)
        # return
        with self.lock:
            first_window = self.device.dump_window(refresh=True)

        # The large model understands the first window to get the kind of scenarios
        scenario_list = self._understand(goal.get('key'), goal.get('value'), first_window)

        # Determine exploration strategy based on scenario list length
        if len(scenario_list) == 1:
            # Single scenario case
            if self.terminated:
                first_window.audio_type = self._understand_first_window_audio(first_window)
                self.wtg.add_window(first_window)
                self.ability_count.add(first_window.ability)
            else:
                self._explore(scenario_list[0], audio=True, max_steps=goal.get('max_steps'))
        else:
            # Multiple scenarios case
            if self.terminated:
                self._explore((AudioType.VIDEO, audio_off_prompt), audio=False, max_steps=goal.get('max_steps'))
                scenario_list.pop(0)
            # Explore other scenarios
            for index, scenario in enumerate(scenario_list):
                self._explore(scenario, audio=True, max_steps=goal.get('max_steps'))
                # After completing each exploration, close all audio and proceed to the next exploration
                if self.terminated and index < len(scenario_list) - 1:
                    self._explore((scenario[0], audio_off_prompt), audio=False, max_steps=goal.get('max_steps'))

        end = time.time()
        logger.debug("events_count: " + str(len(self.events)))
        logger.debug("windows_count: " + str(len(self.wtg.windows)))
        logger.debug("edges_count: " + str(self.edges_count))
        logger.debug("ability_count: " + str(len(self.ability_count)))
        logger.debug("total_time: %.2f seconds" % (end - start))
        WTGParser.dump(self.wtg, goal.get('output_dir'))
        self.close = True
        t1.join(timeout=1)
        return self.wtg

    def _explore(self, scenario, audio, max_steps=20):
        """
        Exploration
        """
        # All completed operations, excluding erroneous operations
        events_without_error = []
        # All completed operations, including erroneous operations
        all_completed_events = []
        # Feedback information
        feedback = []
        # Interface element information
        nodes_before = []
        nodes_description_before = []
        steps = 0

        audio_type = scenario[0]
        scenario = scenario[1]

        while ((not self.terminated) if audio else self.terminated) and steps < max_steps:
            # Get interface before operation execution
            with self.lock:
                window_before = self.device.dump_window(refresh=True)
                if self.terminated:
                    window_before.audio_type = audio_type
                else:
                    window_before.audio_type = ''

            # Get interface element information (only needed first time, as verify gets post-operation interface info)
            if not nodes_description_before:
                nodes_description_before, nodes_before = self._detect_nodes_description(window_before)

            # Get next operation event, event_explanation converts event to a form easily understood by LLM
            events, event_explanation = self._get_next_event(scenario, nodes_description_before, nodes_before,
                                                             window_before, all_completed_events, feedback)

            # Execute operation
            logger.debug("-----------------------Executing LLM-decided operation-----------------------")
            self.device.execute(events)
            logger.debug(event_explanation)
            all_completed_events.append(event_explanation)
            steps += 1

            # Wait for UI update
            time.sleep(2)
            with self.lock:
                window_after = self.device.dump_window(refresh=True)
            nodes_description_after, nodes_after = self._detect_nodes_description(window_after)

            # Verify operation result
            verify_result = self._verify_event(scenario, event_explanation, window_before, nodes_description_before,
                                               window_after, nodes_description_after)

            # If current operation is valid, add it to the completed operations list
            if verify_result["validity"]:
                events_without_error.extend(events)
                if self.terminated:
                    window_after.audio_type = audio_type
                else:
                    window_after.audio_type = ''
                self.wtg.add_edge(window_before, window_after, events)
                self.ability_count.add(window_before.ability)
                self.ability_count.add(window_after.ability)
                self.edges_count += 1

            # If verification result is complete, end exploration
            # if verify_result["goal_completion"] or (isinstance(events[0], KeyEvent) and events[0].key == SystemKey.HOME):
            #     break

            nodes_description_before, nodes_before = nodes_description_after, nodes_after

            feedback.clear()
            feedback.append("Analysis of the previous operation: " + verify_result["analysis"] + "\n")
            feedback.append("Suggested Next Steps: " + verify_result["next_steps"])
            logger.debug(f"Feedback: {feedback}")

        self.events.extend(events_without_error)

    def _should_terminate_thread(self, goal):
        while not self.close:
            with self.lock:
                window = self.device.dump_window(refresh=True)
            if goal.get('key') == ExploreGoal.TESTCASE:
                return False
            if goal.get('key') == ExploreGoal.HARDWARE:
                if goal.get('value') == ResourceType.AUDIO:
                    status = window.rsc.get(ResourceType.AUDIO)
                    if status in [AudioStatus.START, AudioStatus.START_, AudioStatus.DUCK]:
                        logger.debug("Audio is playing")
                        self.terminated = True
                    else:
                        logger.debug("Audio is not playing")
                        self.terminated = False
            time.sleep(1)

    def _understand_first_window_audio(self, first_window):
        """
        Understand the audio type of the first window
        """
        content = [
            {"type": "text", "text": first_window_audio_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(first_window.img)}"}}
        ]
        return self._ask(content)

    def test(self, **goal):
        print(self._understand_first_window_audio(self.device.dump_window(refresh=True)))

    def _understand(self, key, value, first_window=None):
        """
        Understand value to build scenario
        """
        logger.debug("-----------------------Building scenario based on value-----------------------")
        scenario_list = []
        if key == ExploreGoal.TESTCASE:
            understanding_prompt = test_understanding_prompt.format(value)
            content = [{"type": "text", "text": understanding_prompt}]
            scenario_list.append(self._ask(content))
            logger.debug(scenario_list)
            return scenario_list
        elif key == ExploreGoal.HARDWARE:
            content = [
                {"type": "text", "text": first_window_understanding_prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/jpeg;base64,{encode_image(first_window.img)}"}}
            ]
            audio_kind_str = self._ask(content)
            # parse audio_kind_str to list
            audio_kind_list = eval(audio_kind_str)
            if value == ResourceType.AUDIO:
                for app_kind in audio_kind_list:
                    if app_kind == 'Navigation':
                        scenario_list.append((AudioType.NAVIGATION, navigation_audio_prompt))
                    elif app_kind == 'Music':
                        scenario_list.append((AudioType.MUSIC, music_audio_prompt))
                    elif app_kind == 'Video':
                        scenario_list.append((AudioType.VIDEO, video_audio_prompt))
                    elif app_kind == 'Communication':
                        scenario_list.append((AudioType.COMMUNICATION, communication_audio_prompt))
            elif value == ResourceType.CAMERA:
                scenario_list.append(camera_prompt)
            elif value == ResourceType.MICRO:
                scenario_list.append(micro_prompt)
            elif value == ResourceType.KEYBOARD:
                scenario_list.append(keyboard_prompt)
            else:
                logger.debug("Unknown hardware resource")
            logger.debug(audio_kind_str)
            return scenario_list

    def _detect_nodes_description(self, window):
        """
        Detect widgets that match the description
        """
        logger.debug("-----------------------Widgets detection-----------------------")
        nodes = window(clickable='true', enabled='true')
        screenshot = window.img
        node_images = []
        nodes_description = []
        for index, node in enumerate(nodes):
            node_text = self._extract_nodes_text(node)
            node_description = {
                'id': index,
                'type': node.attribute['type'],
                'content': '',
            }
            if 'LinearLayout' in node_description['type']:
                continue
            if node_text:
                node_description['content'] = ', '.join(node_text) if node_text else ''
            else:
                node_description['content'] = 'Image'
                node_images.append(_crop(screenshot, node.attribute['bounds']))
            nodes_description.append(node_description)
        if node_images:
            images_description = self._get_image_description(screenshot, node_images)
            index = 0
            for node_description in nodes_description:
                if node_description['content'] == 'Image':
                    node_description['content'] = images_description[index]
                    index += 1
        # Display clickable controls
        # for image in images:
        #     cv2.imshow('image', image)
        #     cv2.waitKey(0)
        #     cv2.destroyAllWindows()
        logger.debug(nodes_description)
        return nodes_description, nodes

    def _extract_nodes_text(self, node):
        """
        Recursively extract all text from node and its children
        """
        texts = []

        # If current node has text, add to list
        if 'text' in node.attribute and node.attribute['text']:
            texts.append(node.attribute['text'])

        # Recursively process all child nodes
        for child in node._children:
            texts.extend(self._extract_nodes_text(child))
        return texts

    def _get_image_description(self, screenshot, nodes):
        """
        Send screenshot and multiple control screenshots to LLM, get description list for each control
        """
        # Get component count
        nodes_count = len(nodes)

        # Use template imported from prompt.py
        description_prompt = image_description_prompt.format(component_count=nodes_count)

        # Prepare message content
        content = [{"type": "text", "text": description_prompt},
                   {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(screenshot)}"}}]

        # Add screenshot for each control
        for i, component in enumerate(nodes):
            content.append({"type": "text", "text": f"Component {i + 1} of {nodes_count}:"})
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(component)}"}})
        response_text = self._ask(content)
        try:
            match = re.search(r'\[(.*)]', response_text, re.DOTALL)
            if match:
                items_str = match.group(1)
                items = re.findall(r'\'([^\']*?)\'|\"([^\"]*?)\"', items_str)
                descriptions = [item[0] if item[0] else item[1] for item in items]
                return descriptions
            else:
                # If list format not found, return empty list
                return ["Unknown function"] * len(nodes)
        except Exception as e:
            logger.debug(f"Error parsing response: {e}")
            return ["Unknown function"] * len(nodes)

    def _get_next_event(self, scenario, nodes_description, nodes, window, all_completed_events=None, feedback=None):
        """
        Use LLM to decide next operation event
        """
        logger.debug("-----------------------LLM deciding next operation-----------------------")

        if all_completed_events is None:
            all_completed_events = []

        if feedback is None:
            feedback = []

        # Build prompt
        prompt = next_event_prompt.format(scenario, nodes_description, all_completed_events, feedback)

        # Prepare message content
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{encode_image(window.img)}"}}]
        event_str = self._ask(content)
        try:
            event_json = json.loads(event_str)
        except json.JSONDecodeError as e:
            event_json = json.loads(re.search(r'\{.*}', event_str, re.DOTALL).group(0))
        logger.debug(f"Next action returned by LLM: {str(event_json)}", )

        events_list = []
        event_explanation = ''

        # Parse JSON returned by LLM
        event_type = event_json.get("event_type")
        if event_type == "click":
            element_id = event_json.get("element_id")
            if element_id is not None and 0 <= element_id <= len(nodes_description) - 1:
                node = nodes[element_id]
                events_list.append(ClickEvent(node))
                # Build operation description, easy for LLM to understand
                event_explanation = f"Click widget{element_id}: {nodes_description[element_id]['content']} at ({node.attribute['center']})"

        elif event_type == "input":
            element_id = event_json.get("element_id")
            text = event_json.get("text", "")
            if element_id is not None and 0 <= element_id <= len(nodes_description) - 1:
                node = nodes[element_id]
                if node.attribute['focused'] == 'false':
                    events_list.append(ClickEvent(node))
                events_list.append(InputEvent(node, text))
                event_explanation = f"Input text '{text}' into widget{element_id}: {nodes_description[element_id]['content']}"

        elif event_type == "swipe":
            direction = event_json.get("direction")
            if direction in ["left", "right", "up", "down"]:
                events_list.append(SwipeExtEvent(self.device, window, SwipeDirection(direction)))
                event_explanation = f"Swipe {direction} to the screen"

        elif event_type == "back":
            event_explanation = "Go back to the previous screen"
            events_list.append(KeyEvent(self.device, window, SystemKey.BACK))

        elif event_type == "home":
            event_explanation = "Return to the home screen"
            events_list.append(KeyEvent(self.device, window, SystemKey.HOME))

        return events_list, event_explanation

    def _verify_event(self, scenario, event_explanation, window_before, nodes_description_before, window_after,
                      nodes_description_after):
        """
        Verify operation result
        """
        logger.debug("-----------------------Verifying operation result-----------------------")

        before_image_base64 = encode_image(window_before.img)
        before_image_content = f"data:image/jpeg;base64,{before_image_base64}"

        after_image_base64 = encode_image(window_after.img)
        after_image_content = f"data:image/jpeg;base64,{after_image_base64}"

        # Build prompt
        prompt = verify_prompt.format(scenario, event_explanation, nodes_description_before,
                                      nodes_description_after)

        content = [{"type": "text", "text": prompt},
                   {"type": "image_url", "image_url": {"url": before_image_content}},
                   {"type": "image_url", "image_url": {"url": after_image_content}}]

        verify_result_str = self._ask(content)
        logger.debug(f"Verification result: {verify_result_str}")

        # Parse JSON
        verify_result_json = re.search(r'\{.*}', verify_result_str, re.DOTALL)
        if verify_result_json:
            verify_result = json.loads(verify_result_json.group(0))
            return verify_result
