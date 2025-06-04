import subprocess
import time

from loguru import logger
from hmbot.explorer.llm import GeneralLLM, SpecializedLLM
import re
import json
from hmbot.explorer.prompt import *
from hmbot.cv import encode_image


class Agent(object):
    def __init__(self):
        pass


class MobilePhoneAgent(Agent):
    def __init__(self, device=None):
        super().__init__()
        self.llm = SpecializedLLM()
        self.device = device

    def explore(self, scenario):
        """
        Explore the mobile phone
        """
        page = self.device.dump_page(refresh=True)
        screenshot = page.img
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
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image(screenshot)}",
                        }
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
    def __init__(self):
        super().__init__()
        self.llm = GeneralLLM()

    def test(self, scenario):
        """
        Test the hardware
        """
        pass


class AppTestAgent(Agent):
    def __init__(self):
        super().__init__()
        self.llm = GeneralLLM()

    def test(self, scenario):
        """
        Test the app
        """
        pass


class UserTaskAgent(Agent):
    def __init__(self):
        super().__init__()
        self.llm = GeneralLLM()
    
    def task(self, request):
        """
        Task the request
        """
        pass


class MultiAgent:
    def __init__(self, device=None):
        self.device = device
        self.classify_agent = ClassifyAgent()
        self.user_task_agent = UserTaskAgent()
        self.hardware_test_agent = HardwareTestAgent()
        self.app_test_agent = AppTestAgent()
        
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