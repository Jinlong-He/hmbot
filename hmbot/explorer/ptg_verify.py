import time
import json
import re
import os
import zss
import cv2
import numpy as np
from loguru import logger
from pydantic import SecretStr
from hmbot.model.event import ClickEvent
from hmbot.model.vht import VHTNode
from hmbot.utils.cv import encode_image
from hmbot.model.ptg import PTGParser
from hmbot.explorer.prompt import *
from dotenv import load_dotenv
from langchain.schema import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
event_llm = ChatOpenAI(
    model=os.getenv("SPECIALIZED_MODEL") or "gpt-4o",
    base_url=os.getenv("SPECIALIZED_BASE_URL") or "https://api.openai.com/v1",
    api_key=SecretStr(os.getenv("SPECIALIZED_API_KEY") or ""),	
)


class PTG_IR(object):
    def __init__(self, ptg):
        self.pages = []
        self.transitions = {}
        self._ptg_to_ir(ptg)

    def _ptg_to_ir(self, ptg):
        for page in ptg.pages:
            self.pages.append(page)
            if page.id not in self.transitions:
                self.transitions[page.id] = {}
            
            if page in ptg._adj_list:
                for tgt_page, events in ptg._adj_list[page].items():
                    self.transitions[page.id][tgt_page.id] = events

    def print_ir(self):
        for page in self.pages:
            print(f"Page: {page.id}")
            if page.id in self.transitions and self.transitions[page.id]:
                for tgt_page_id, transition in self.transitions[page.id].items():
                    print(f"  Transition to: {tgt_page_id}")
                    print(f"    Events: {transition}")
            else:
                print(f"  No outgoing transitions")
            

class PTGVerifier:
    def __init__(self, device, ptg_dir_path):
        """
        Initialize the PTGVerifier

        Args:
            device: Device object, the device to execute the operation
            ptg_dir_path: str, the path to the PTG directory
        """
        self.device = device
        # self.ptg = PTGParser.parse(device, ptg_dir_path)
        self.ptg_ir = PTG_IR(PTGParser.parse(device, ptg_dir_path))
        # self.ptg_ir.print_ir()
        self.visited_pages_id = set()
        
    def verify_ptg_dfs(self, page_before=None):
        """
        Verify the PTG using DFS algorithm

        Args:
            page_before: Page object, the page to start from, if not provided, start from the first page

        page_before -> page_after
                    |
                    |->current_page

        """
        if page_before is None:
            page_before = self.ptg_ir.pages[0]

        # Mark current page as visited
        self.visited_pages_id.add(page_before.id)
        logger.info(f"Visiting page id: {page_before.id}")

        # Update page_before with the current page
        self._update_page(page_before)
        
        if page_before.id in self.ptg_ir.transitions:
            # Check all adjacent pages and events of current page
            for page_after_id, events in self.ptg_ir.transitions[page_before.id].items():
                logger.info(f"Checking transition to: {page_after_id}")
                
                # If target page is not visited, execute events to reach target page and visit recursively
                if page_after_id not in self.visited_pages_id:
                    logger.info(f"Executing events to reach page_after...")

                    new_events = []
                    page_after = self.ptg_ir.pages[page_after_id]
                    # page_before -> current_page
                    result, error_type, current_page = self._verify_event_with_llm(page_before, page_after, events)

                    retry_count = 0

                    if result:
                        # current_page == page_after
                        logger.info(f"Event verification passed: Successfully reached page_after")
                        self.verify_ptg_dfs(page_after)
                    else:       
                        # current_page != page_after
                        logger.info(f"Event verification failed: {error_type}")
                        # current_page -> page_before
                        if error_type == "wrong_page":
                            current_page.id = len(self.ptg_ir.pages)
                            self.ptg_ir.pages.append(current_page)
                            self.ptg_ir.transitions[page_before.id][current_page.id] = events
                            return_event_command = self._generate_return_event_command(page_before, current_page, events)
                            self._execute_event_command(return_event_command, current_page)
                        # page_before -> page_after
                        while retry_count < 3:
                            next_event_command = self._generate_next_event_command(page_before, page_after)
                            new_events = self._execute_event_command(next_event_command, page_before)
                            result, error_type, current_page = self._verify_event_with_llm(page_before, page_after, new_events)
                            if result:
                                self.ptg_ir.transitions[page_before.id][page_after_id] = new_events
                                self.verify_ptg_dfs(page_after)
                                break
                            else:
                                # current_page -> page_before
                                if error_type == "wrong_page":
                                    return_event_command = self._generate_return_event_command(page_before, current_page, new_events)
                                    self._execute_event_command(return_event_command, current_page)
                            retry_count += 1

                    if retry_count == 0:
                        return_event_command = self._generate_return_event_command(page_before, page_after, events)
                        self._execute_event_command(return_event_command, page_after)
                    elif retry_count == 3:
                        continue
                    else:
                        return_event_command = self._generate_return_event_command(page_before, page_after, new_events)
                        self._execute_event_command(return_event_command, page_after)
        else:
            # if no outgoing transitions, explore new page
            self._explore_new_page(page_before, max_depth=3, current_depth=0)

    def _explore_new_page(self, page, max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return
        
        # Initialize transitions for this page if not exists
        if page.id not in self.ptg_ir.transitions:
            self.ptg_ir.transitions[page.id] = {}
        
        messages = [
            SystemMessage(content=explore_page_events_prompt),
            HumanMessage(
                content=[
                    {"type": "text", "text": "Please analyze this interface screenshot and identify ONLY the most important clickable elements:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(page.img)}"}},
                ]
            ),
        ]
            
        response = llm.invoke(messages)
        response_content = response.text().strip()
        
        if response_content.startswith('```'):
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                response_content = match.group(1).strip()
        result_json = json.loads(response_content)
        clickable_events = result_json.get("clickable_events", [])
        for event in clickable_events:
            logger.info(f"Events of page {page.id}: {event}")
        for event in clickable_events:
            new_events = self._execute_event_command(event, page)
            new_page = self.device.dump_page(refresh=True)
            index = self._is_page_exist(new_page)
            if index == -1:
                new_page.id = len(self.ptg_ir.pages)
                self.ptg_ir.pages.append(new_page)
                self.ptg_ir.transitions[page.id][new_page.id] = new_events
                self._explore_new_page(new_page, max_depth, current_depth + 1)
            else:
                self.ptg_ir.transitions[page.id][index] = new_events
            return_event_command = self._generate_return_event_command(page, new_page, new_events)
            self._execute_event_command(return_event_command, new_page)
            
    def _update_page(self, page):
        """
        Update the page with the current page from the device
        """
        current_page = self.device.dump_page(refresh=True)
        page.img = current_page.img
        page.vht = current_page.vht
        page.info = current_page.info

    def _is_page_exist(self, current_page):
        """
        Check if the page exists in the PTG
        """
        for page in reversed(self.ptg_ir.pages):
            if self._is_pages_same(page, current_page):
                return page.id
        return -1

    def _is_pages_same(self, page1, page2):
        """
        Check if the two pages are the same
        """
        distance = zss.simple_distance(page1.vht._root, page2.vht._root, get_children=VHTNode.get_children, get_label=VHTNode.get_label)
        logger.info(f"Distance between page1 and page2: {distance}")
        distance_value = distance[0] if isinstance(distance, tuple) else distance
        
        if distance_value < 3:
            return True
        elif distance_value > 30:
            return False
        else:
            # When tree structure is similar, use LLM to verify if they are the same interface
            return self._verify_same_page_with_llm(page1, page2)

    def _verify_same_page_with_llm(self, page1, page2):
        """
        Use LLM to verify if two pages are the same interface
        Focus on layout structure rather than content
        """
        messages = [
            SystemMessage(content=verify_same_page_prompt),
            HumanMessage(content=[
                {"type": "text", "text": "First interface screenshot:"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(page1.img)}"}},
                {"type": "text", "text": "Second interface screenshot:"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(page2.img)}"}},
                {"type": "text", "text": "Please determine whether these two interfaces are the same interface?"}
            ])
        ]
        
        response = llm.invoke(messages)
        response_content = response.text().strip()
        
        if response_content.startswith('```'):
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                response_content = match.group(1).strip()
        
        try:
            result_json = json.loads(response_content)
            is_same = result_json.get("is_same", False)
            logger.info(f"LLM page comparison result: {is_same}")
            return is_same
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response_content}")
            return False
            
    def test(self):
        # cv2.imshow('page1', page1.img)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        # page2 = self.device.dump_page(refresh=True)
        # cv2.imshow('page2', page2.img)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # self._is_pages_same(page1, page2)
        page = self.device.dump_page(refresh=True)
        page.id = len(self.ptg_ir.pages)
        self.ptg_ir.pages.append(page)
        self._explore_new_page(page, max_depth=3, current_depth=0)
        self.ptg_ir.print_ir()

    def _verify_event_with_llm(self, page_before, page_after, events):
        """
        Verify the event with LLM

        Args:
            page_before: Page object, the page before the event is executed
            page_after: Page object, the page after the event is executed
            events: List of events to be executed between page_before and page_after
        """
        logger.info("=====================event verify===========================")
        self.device.execute(events)
        time.sleep(3)
        current_page = self.device.dump_page(refresh=True)
        messages = [
            SystemMessage(content=verify_ptg_system_prompt),
            HumanMessage(
                content=[
                    {"type": "text", "text": "First image: PTG before node screenshot"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(page_before.img)}"}},
                    {"type": "text", "text": "Second image: PTG after node screenshot"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(page_after.img)}"}},
                    {"type": "text", "text": "Third image: screenshot after actual event execution"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(current_page.img)}"}},
                ]
            ),
        ]
            
        response = llm.invoke(messages)
        response_content = response.text().strip()
        
        if response_content.startswith('```'):
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                response_content = match.group(1).strip()
        
        result_json = json.loads(response_content)
        think = result_json.get("think", "")
        result = result_json.get("result", False)
        error_type = result_json.get("error_type", "")
        
        logger.info(f"Analysis process: {think}")
        logger.info(f"Verification result: {'Pass' if result else 'Failed'}")
        logger.info(f"Error type: {error_type}")
        return result, error_type, current_page

    def _generate_next_event_command(self, page_before, page_after):
        """
        Generate the next event command

        Args:
            page_before: Page object, the page before the event is executed
            page_after: Page object, the page after the event is executed

        Returns:
            str: The next event command in natural language
        """
        logger.info("=====================generate next event command===========================")
        messages = [
            SystemMessage(content=generate_next_event_prompt),
            HumanMessage(content=[
                {"type": "text", "text": "First image: page before action"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(page_before.img)}"}},
                {"type": "text", "text": "Second image: page after action"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(page_after.img)}"}},
            ]),
        ]
        response = llm.invoke(messages)
        logger.info(f"Generated next operation command: {response.text()}")
        return response.text()

    def _generate_return_event_command(self, page_before, current_page, events):
        """
        Generate the return event command

        Args:
            page_before: Page object, the page after the return event is executed
            current_page: Page object, the page before the return event is executed
            events: List of events to be executed between page_before and current_page

        Returns:
            str: The return event command in natural language
        """
        logger.info("=====================generate return event command===========================")
       
        # Create image with red boxes marking event locations
        marked_image = self._draw_event_boxes_on_image(page_before.img, events)
        
        messages = [
            SystemMessage(content=generate_return_operation_prompt),
            HumanMessage(content=[
                {"type": "text", "text": "Target page (the page we want to return to, the page before the action is executed). The red boxes mark the locations that were clicked to transition from target page to current page."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{marked_image}"}},
                {"type": "text", "text": "Current page (the page after the action is executed, need to return to the target page)"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(current_page.img)}"}},
            ]),
        ]
        response = llm.invoke(messages)
        logger.info(f"Generated return operation command: {response.text()}")
        return response.text()

    def _draw_event_boxes_on_image(self, image, events):
        """
        Draw red boxes on the image to mark event locations
        
        Args:
            image: numpy array, the original image
            events: List of events containing coordinates
            
        Returns:
            str: base64 encoded image with red boxes
        """
        if not events:
            return encode_image(image)
            
        # Make a copy of the image to avoid modifying the original
        marked_image = image.copy()
        
        for event in events:
            if hasattr(event, 'node') and hasattr(event.node, 'attribute'):
                bounds = event.node.attribute.get('bounds', None)
                if bounds and len(bounds) == 2:
                    # Extract coordinates from bounds [[x1, y1], [x2, y2]]
                    x1, y1 = bounds[0]
                    x2, y2 = bounds[1]
                    
                    # Draw red rectangle
                    cv2.rectangle(marked_image, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    cv2.imshow('marked_image', marked_image)
                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                    break
        
        return encode_image(marked_image)

    def _execute_event_command(self, command, current_page):
        """
        Execute the event command

        Args:
            command: str, the event command in natural language
            current_page: Page object, the page before the event is executed

        Returns:
            List of events have been executed
        """
        logger.info("=====================execute event command===========================") 
        message_history = [
            SystemMessage(content=event_llm_prompt),
            HumanMessage(content=command)
        ]
        
        parsed_output = {"action": ""}
        new_events = []
        while parsed_output["action"] != "finished":
            screenshot = self.device.screenshot()
            base64_image = encode_image(screenshot)
            
            current_message = HumanMessage(content=[
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    }
                }
            ])
            message_history.append(current_message)
            
            response = event_llm.invoke(message_history)
            parsed_output = json.loads(parse_action_output(response.text()))
            
            if parsed_output["action"] != "finished":
                logger.info(f"Executing event: {parsed_output}")
                new_events.append(phone_operation(parsed_output, current_page.img.shape, self.device, current_page))
            
            message_history.append(response)
            
        return new_events


def is_node_exist(page, event):
    """
    Check if a node in an event exists in a page
    
    Args:
        page: Page object, containing VHT (View Hierarchy Tree) structure
        event: Event object, containing node information
    
    Returns:
        bool: True if node exists, False otherwise
    """
    event_node = event.node
    event_attrs = event_node.attribute

    target_id = event_attrs.get('id', '')
    target_bounds = event_attrs.get('bounds', '')
    target_text = event_attrs.get('text', '')
    target_type = event_attrs.get('type', '')
    target_clickable = event_attrs.get('clickable', '')

    
    def _match_node(node_attrs, target_attrs):
        """
        Compare two nodes to see if they match
        Must match all key attributes
        """
        # If ID exists and is not empty, it must match exactly
        if target_attrs.get('id') and node_attrs.get('id'):
            if node_attrs.get('id') != target_attrs.get('id'):
                return False
        
        # Check boundary position - must match exactly
        if target_attrs.get('bounds') and node_attrs.get('bounds'):
            if node_attrs.get('bounds') != target_attrs.get('bounds'):
                return False
        
        # Check text content - must match exactly
        if target_attrs.get('text') and node_attrs.get('text'):
            if node_attrs.get('text') != target_attrs.get('text'):
                return False
        
        # Check element type - must match exactly
        if target_attrs.get('type') and node_attrs.get('type'):
            if node_attrs.get('type') != target_attrs.get('type'):
                return False

        # Check clickable attribute - must match exactly
        if target_attrs.get('clickable') and node_attrs.get('clickable'):
            if node_attrs.get('clickable') != target_attrs.get('clickable'):
                return False
        
        # All checked attributes match
        return True
    
    def _search_in_vht(vht_node, target_attrs):
        # Check current node
        if hasattr(vht_node, 'attribute'):
            if _match_node(vht_node.attribute, target_attrs):
                return True
        
        # Recursively check child nodes
        if hasattr(vht_node, '_children'):
            for child in vht_node._children:
                if _search_in_vht(child, target_attrs):
                    return True
        
        return False
    
    # Search for nodes in the VHT of the page
    try:
        if hasattr(page, 'vht') and hasattr(page.vht, '_root'):
            target_attrs = {
                'id': target_id,
                'bounds': target_bounds,
                'text': target_text,
                'type': target_type,
                'clickable': target_clickable
            }
            return _search_in_vht(page.vht._root, target_attrs)
        else:
            return False
    except Exception as e:
        print(f"Error in is_node_exist: {e}")
        return False

def extract_node_by_coordinates(click_x, click_y, page):
    """
    Extract the node by coordinates

    Args:
        click_x: int, the x coordinate of the click
        click_y: int, the y coordinate of the click
        page: Page object, the page to extract the node from

    Returns:
        VHTNode object, the node extracted from the page
    """
    def point_in_bounds(x, y, bounds):
        if not bounds or len(bounds) != 2:
            return False
        
        x1, y1 = bounds[0]
        x2, y2 = bounds[1]
        
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def find_node_by_coordinates(vht_node, x, y):
        candidates = []  
        
        def collect_clickable_candidates(node, x, y, candidates_list):
            if hasattr(node, 'attribute') and 'bounds' in node.attribute:
                bounds = node.attribute['bounds']
                
                # Exclude invalid bounds [0, 0][0, 0] of root node
                if bounds == [[0, 0], [0, 0]]:
                    if hasattr(node, '_children'):
                        for child in node._children:
                            collect_clickable_candidates(child, x, y, candidates_list)
                    return
                
                if point_in_bounds(x, y, bounds):
                    # If current node is clickable, add to candidate list
                    if (hasattr(node, 'attribute') and 
                        node.attribute.get('clickable') == 'true'):
                        candidates_list.append(node)
                    
                    # Continue searching child nodes
                    if hasattr(node, '_children'):
                        for child in node._children:
                            collect_clickable_candidates(child, x, y, candidates_list)
        
        def calculate_area(bounds):
            if not bounds or len(bounds) != 2:
                return float('inf')  # Return infinite area for invalid bounds
            x1, y1 = bounds[0]
            x2, y2 = bounds[1]
            return (x2 - x1) * (y2 - y1)
        
        # Collect all candidate nodes
        collect_clickable_candidates(vht_node, x, y, candidates)
        
        # If no candidate nodes, return None
        if not candidates:
            return None
        
        # Find candidate node with smallest area
        min_area = float('inf')
        best_candidate = None
        
        for candidate in candidates:
            if hasattr(candidate, 'attribute') and 'bounds' in candidate.attribute:
                area = calculate_area(candidate.attribute['bounds'])
                # print(f"Candidate bounds: {candidate.attribute['bounds']}, area: {area}")
                if area < min_area:
                    min_area = area
                    best_candidate = candidate
        
        return best_candidate
    
    try:
        if hasattr(page, 'vht') and hasattr(page.vht, '_root'):
            return find_node_by_coordinates(page.vht._root, click_x, click_y)
        else:
            logger.error("Page does not have valid VHT structure")
            return None
    except Exception as e:
        logger.error(f"Error in extract_node: {e}")
        return None

def phone_operation(parsed_output, shape, device, page):
    """
    Execute the phone operation

    Args:
        parsed_output: dict, the parsed output of the action
        shape: tuple, the shape of the image
        device: Device object, the device to execute the operation
        page: Page object, the page to execute the operation

    Returns:
        Event object, the event executed
    """
    start_abs = coordinates_convert(parsed_output["start_box"], (shape[1], shape[0])) if parsed_output["start_box"] else None
    end_abs = coordinates_convert(parsed_output["end_box"], (shape[1], shape[0])) if parsed_output["end_box"] else None
    direction = parsed_output["direction"] if parsed_output["direction"] else None

    if parsed_output["action"] == "click" and start_abs:
        center_pos = (
            (start_abs[0] + start_abs[2]) // 2,
            (start_abs[1] + start_abs[3]) // 2
        )
        logger.info(f"Click coordinates: {center_pos}")
        node = extract_node_by_coordinates(center_pos[0], center_pos[1], page)
        # print(f"Extracted node: {node.attribute['bounds']}")
        new_event = ClickEvent(node)
        new_event.execute()
        # device.click(*center_pos)
        time.sleep(3)
        return new_event
    elif parsed_output["action"] == "input" and parsed_output["content"]:
        device.input(parsed_output["content"])
        time.sleep(3)
        return None
    elif parsed_output["action"] == "swipe" and start_abs and end_abs:
        device.swipe(start_abs[0], start_abs[1], end_abs[0], end_abs[1])
        time.sleep(3)
        return None
    
def parse_action_output(output_text):
    """
    Parse the output text of the action

    Args:
        output_text: str, the output text of the action

    Returns:
        dict, the parsed output of the action
    """
    thought_match = re.search(r'Thought:(.*?)\nAction:', output_text, re.DOTALL)
    thought = thought_match.group(1).strip() if thought_match else ""

    action_match = re.search(r'Action:(.*?)(?:\n|$)', output_text, re.DOTALL)
    action_text = action_match.group(1).strip() if action_match else ""

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

    action_parts = action_text.split('(')
    action_type = action_parts[0]
    result["action"] = action_type

    if len(action_parts) > 1:
        params_text = action_parts[1].rstrip(')')
        params = {}

        for param in params_text.split(','):
            param = param.strip()
            if '=' in param:
                key, value = param.split('=', 1)
                key = key.strip()
                value = value.strip().strip('\'"')

                if 'box' in key:
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
    if len(relative_bbox) != 4 or len(img_size) != 2:
        raise ValueError("Input parameter format should be: relative_bbox=[x1,y1,x2,y2], img_size=(width,height)")
        
    img_width, img_height = img_size
    
    abs_x1 = int(relative_bbox[0] * img_width / 1000)
    abs_y1 = int(relative_bbox[1] * img_height / 1000)
    abs_x2 = int(relative_bbox[2] * img_width / 1000)
    abs_y2 = int(relative_bbox[3] * img_height / 1000)
    
    return [abs_x1, abs_y1, abs_x2, abs_y2]
    


