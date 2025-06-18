import subprocess
import time
from loguru import logger
from hmbot.explorer.llm import GeneralLLM, SpecializedLLM
import re
import json
from hmbot.explorer.prompt import *
from hmbot.utils.cv import encode_image


class Agent(object):
    def __init__(self):
        self.llm = None

    def _build_scenario(self, request, type):
        """
        Build scenario for LLM
        """
        logger.debug("-----------------------Building scenario-----------------------")
        # Optimize user request
        request = optimize_user_request.format(user_request=request)
        messages = [
            {
                "role": "system",
                "content": "You are an expert in optimizing large model prompts."
            },
            {
                "role": "user",
                "content": request
            }
        ]
        optimized_request = self.llm.ask(messages)
        # Understand user request
        if type == "user_task":
            request = user_task_prompt.format(request=optimized_request)
        elif type == "hardware_test":
            request = hardware_test_prompt.format(request=optimized_request)
        elif type == "app_test":
            request = app_test_prompt.format(request=optimized_request)
        messages = [
            {
                "role": "system",
                "content": "You are an expert in understanding user requests."
            },
            {
                "role": "user",
                "content": request
            }
        ]
        scenario = self.llm.ask(messages)
        return scenario


class MobilePhoneAgent(Agent):
    def __init__(self, device=None):
        super().__init__()
        self.llm = SpecializedLLM()
        self.device = device

    def explore(self, scenario):
        """
        Explore the mobile phone
        """
        # get screenshot and resource status
        page = self.device.dump_page(refresh=True)
        screenshot = page.img
        resource_status = page.rsc

        messages=[
            {
                "role": "system",
                "content": phone_operation_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": scenario
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image(screenshot)}",
                        }
                    },
                    {
                        "type": "text",
                        "text": "Resource status: " + str(resource_status)
                    }
                ]
            }
        ]
        
        parsed_output = {"action": ""}
        while parsed_output["action"] != "finished":
            response = self.llm.ask(messages)
            print("【Results】\n", response)
            messages.append({
                "role": "assistant",
                "content": response
            })
            parsed_output = json.loads(self.parse_action_output(response))
            print("parsed_output: ", parsed_output)

            # Convert coordinates
            start_abs = self.coordinates_convert(parsed_output["start_box"], screenshot.shape[:2]) if parsed_output["start_box"] else None
            end_abs = self.coordinates_convert(parsed_output["end_box"], screenshot.shape[:2]) if parsed_output["end_box"] else None
            direction = parsed_output["direction"] if parsed_output["direction"] else None

            if parsed_output["action"] == "click" and start_abs:
                # Calculate click center using converted absolute coordinates
                center_pos = (
                    (start_abs[0] + start_abs[2]) // 2,
                    (start_abs[1] + start_abs[3]) // 2
                )
                print(f"Click coordinates: {center_pos}")
                # Execute click operation
                self.device.click(*center_pos)
            time.sleep(3)

            page = self.device.dump_page(refresh=True)
            screenshot = page.img
            resource_status = page.rsc
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image(screenshot)}",
                        }
                    },
                    {
                        "type": "text",
                        "text": "Resource status: " + str(resource_status)
                    }
                ]
            })

            

    def parse_action_output(output_text):
        """
        Parse the output text of the action
        """
        # Extract Thought section
        thought_match = re.search(r'Thought:(.*?)\nAction:', output_text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else ""

        # Extract Action section
        action_match = re.search(r'Action:(.*?)(?:\n|$)', output_text, re.DOTALL)
        action_text = action_match.group(1).strip() if action_match else ""

        # Initialize result dictionary
        result = {
            "thought": thought,
            "action": "",
            "key": None,
            "content": None,
            "start_box": None,
            "end_box": None,
            "direction": None
        }

        if not action_text:
            return json.dumps(result, ensure_ascii=False)

        # Parse action type
        action_parts = action_text.split('(')
        action_type = action_parts[0]
        result["action"] = action_type

        # Parse parameters
        if len(action_parts) > 1:
            params_text = action_parts[1].rstrip(')')
            params = {}

            # Process key-value parameters
            for param in params_text.split(','):
                param = param.strip()
                if '=' in param:
                    key, value = param.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('\'"')

                    # Handle bbox format
                    if 'box' in key:
                        # Extract coordinate numbers
                        numbers = re.findall(r'\d+', value)
                        if numbers:
                            coords = [int(num) for num in numbers]
                            if len(coords) == 4:
                                if key == 'start_box':
                                    result["start_box"] = coords
                                elif key == 'end_box':
                                    result["end_box"] = coords
                    elif key == 'key':
                        result["key"] = value
                    elif key == 'content':
                        # Process escape characters
                        value = value.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")
                        result["content"] = value
                    elif key == 'direction':
                        result["direction"] = value

        return json.dumps(result, ensure_ascii=False, indent=2)

    def coordinates_convert(relative_bbox, img_size):
        """
        Convert relative coordinates [0,1000] to absolute pixel coordinates on the image
        
        Parameters:
            relative_bbox: Relative coordinate list/tuple [x1, y1, x2, y2] (range 0-1000)
            img_size: Image dimension tuple (width, height)
            
        Returns:
            Absolute coordinate list [x1, y1, x2, y2] (unit: pixels)
            
        Example:
            >>> coordinates_convert([500, 500, 600, 600], (1000, 2000))
            [500, 1000, 600, 1200]  # For an image with height 2000, y-coordinates are multiplied by 2
        """
        # Parameter validation
        if len(relative_bbox) != 4 or len(img_size) != 2:
            raise ValueError("Input parameter format should be: relative_bbox=[x1,y1,x2,y2], img_size=(width,height)")
            
        # Unpack image dimensions
        img_width, img_height = img_size
        
        # Calculate absolute coordinates
        abs_x1 = int(relative_bbox[0] * img_width / 1000)
        abs_y1 = int(relative_bbox[1] * img_height / 1000)
        abs_x2 = int(relative_bbox[2] * img_width / 1000)
        abs_y2 = int(relative_bbox[3] * img_height / 1000)
        
        return [abs_x1, abs_y1, abs_x2, abs_y2]
    

class ClassifyAgent(Agent):
    def __init__(self):
        super().__init__()
        self.llm = GeneralLLM()

    def classify(self, request):
        """
        Classify the scenario
        """
        prompt = classify_agent_prompt.format(request=request)
        messages = [
            {
                "role": "system",
                "content": "You are a mobile phone app GUI tester."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        response = self.llm.ask(messages)
        # parse json
        try:
            response = json.loads(response)
        except json.JSONDecodeError as e:
            response = json.loads(re.search(r"\{.*}", response, re.DOTALL).group(0))
        logger.debug(f"User request={request}\nClassify result: category={response['category']}")
        return response


class HardwareTestAgent(Agent):
    def __init__(self, explore_agent):
        super().__init__()
        self.llm = GeneralLLM()
        self.explore_agent = explore_agent

    def test(self, request):
        """
        Test the hardware
        """
        logger.debug("-----------------------Hardware test-----------------------")
        page = self.device.dump_page(refresh=True)
        screenshot = page.img
        messages = [
            {
                "role": "system",
                "content": "You are a mobile phone hardware tester."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "User request: " + request},
                    {"type": "text", "text": first_window_understanding_prompt},
                    {"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encode_image(screenshot)}"}}
                ]
            }
        ]
        response = self.llm.ask(messages)
        messages.append({
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": response
                }
            ]
        })  
        try:
            audio_kind_list = json.loads(response)
        except json.JSONDecodeError:
            json_str = re.search(r'\[.*?\]', response).group()
            audio_kind_list = json.loads(json_str)
        logger.debug(f"Audio types identified: {audio_kind_list}")

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": hardware_understand_prompt.format(request=request)
                }
            ]
        })  
        response = self.llm.ask(messages)
        
        try:
            hardware_list = json.loads(response)
        except json.JSONDecodeError as e:
            json_match = re.search(r'\[.*?\]', response)
            if json_match:
                hardware_list = json.loads(json_match.group())
            else:
                hardware_list = []

        scenario_list = []
        for hardware in hardware_list:
            if hardware == "AUDIO":
                for audio_kind in audio_kind_list:
                    if audio_kind == "Navigation":
                        scenario_list.append((AudioType.NAVIGATION, navigation_audio_prompt))
                    elif audio_kind == "Music":
                        scenario_list.append((AudioType.MUSIC, music_audio_prompt))
                    elif audio_kind == "Video":
                        scenario_list.append((AudioType.VIDEO, video_audio_prompt))
                    elif audio_kind == "Communication":
                        scenario_list.append((AudioType.COMMUNICATION, communication_audio_prompt))
            elif hardware == "CAMERA":
                scenario_list.append(camera_prompt)
            elif hardware == "MICRO":
                scenario_list.append(micro_prompt)
            elif hardware == "KEYBOARD":
                scenario_list.append(keyboard_prompt)
            else:
                logger.debug("Unknown hardware resource")
        for scenario in scenario_list:
            self.explore_agent.explore(scenario)
            # Close the app and open it again
            # self.device.automator.close_app(app_package_name)
            # self.device.automator.start_app(app_package_name)


class AppTestAgent(Agent):
    def __init__(self, explore_agent):
        super().__init__()
        self.llm = GeneralLLM()
        self.explore_agent = explore_agent

    def test(self, request):
        """
        Test the app
        """
        logger.debug("-----------------------App test-----------------------")
        # Build scenario
        scenario_str = self._build_scenario(request, "app_test")
        logger.debug(scenario_str)
        
        # Parse scenario
        try:
            scenarios = json.loads(scenario_str)
        except json.JSONDecodeError:
            json_pattern = r'\[\s*\{.*\}\s*\]'
            json_match = re.search(json_pattern, scenario_str, re.DOTALL)
            if json_match:
                try:
                    scenarios = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    json_str = re.search(r'\[\s*{.*}\s*\]', scenario_str, re.DOTALL | re.MULTILINE).group(0)
                    scenarios = json.loads(json_str)
            else:
                logger.error("Failed to extract JSON from response")
                return
                    
        # Explore the app
        for scenario_item in scenarios:
            scenario_name = scenario_item.get("scenario_name", "")
            scenario_data = scenario_item.get("scenario", {})
            
            logger.debug(f"Running scenario: {scenario_name}")
         
            # Explore the app
            self.explore_agent.explore(scenario_data)

            # Close the app and open it again
            # self.device.automator.close_app(app_package_name)
            # self.device.automator.start_app(app_package_name)


class UserTaskAgent(Agent):
    def __init__(self, explore_agent):
        super().__init__()
        self.llm = GeneralLLM()
        self.explore_agent = explore_agent
    
    def task(self, request):
        """
        Task the request
        """
        logger.debug("-----------------------User task-----------------------")
        # Build scenario
        scenario = self._build_scenario(request, "user_task")
        logger.debug(scenario)

        # Explore the app
        self.explore_agent.explore(scenario)

class MultiAgent:
    def __init__(self, device=None):
        self.device = device
        self.explore_agent = MobilePhoneAgent()
        self.classify_agent = ClassifyAgent()
        self.user_task_agent = UserTaskAgent(self.explore_agent)
        self.hardware_test_agent = HardwareTestAgent(self.explore_agent)
        self.app_test_agent = AppTestAgent(self.explore_agent)
        
    def explore(self, request):
        """
        Explore the request
        """
        classify_result = self.classify_agent.classify(request)
        app_name = classify_result.get('target_app', '')
        logger.debug(f"App name: {app_name}")
        # Get all apps
        apps_list = self.device.automator.get_all_apps()
        # Select the app package name from the apps list
        messages = [
            {
                "role": "system",
                "content": "You are a mobile phone app package name finder."
            },
            {
                "role": "user",
                "content": app_selection_prompt.format(target_app=app_name, apps=apps_list)
            }
        ]
        app_package_name = self.llm.ask(messages)
        app_package_name = app_package_name.strip()
        logger.debug(f"App package name: {app_package_name}")
        
        if app_package_name != "ERROR":
            # Start the app through shell
            try:
                subprocess.run([
                    "adb", "shell", "monkey", 
                    "-p", app_package_name, 
                    "-c", "android.intent.category.LAUNCHER", 
                    "1"
                ], check=True, capture_output=True, text=True)                
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to start app {app_package_name}: {e}")
                return
        else:
            logger.error(f"Your device does not have the app {classify_result.get('target_app', '')}")
            return
        if classify_result['category'] == 'USER_TASK':
            self.user_task_agent.task(request)
        elif classify_result['category'] == 'HARDWARE_EXPLORATION':
            self.hardware_test_agent.test(request)
        elif classify_result['category'] == 'TESTING_TASK':
            self.app_test_agent.test(request)