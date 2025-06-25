import time
import json
import re
import os
from loguru import logger
from hmbot.model.event import ClickEvent
from hmbot.utils.cv import encode_image
from hmbot.model.ptg import PTGParser
from hmbot.explorer.prompt import *
from dotenv import load_dotenv
from langchain.schema import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate
# from langchain.memory import ConversationBufferMemory
# from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder


load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
event_llm = ChatOpenAI(
    openai_api_base=os.getenv("SPECIALIZED_BASE_URL"),
    openai_api_key=os.getenv("SPECIALIZED_API_KEY"),	
    model_name=os.getenv("SPECIALIZED_MODEL"),	
)


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
    

def verify_ptg_dfs(device, ptg_dir_path):
    # Parse PTG file
    ptg = PTGParser.parse(device, ptg_dir_path)
    # Record visited pages
    visited_pages_id = set()

    # Depth-first traversal verification function
    def dfs_verify(page_before):
        # Mark current page as visited
        visited_pages_id.add(page_before.id)
        print(f"Visiting page id: {page_before.id}")
        
        # Check all adjacent pages and events of current page
        if page_before in ptg._adj_list:
            for page_after, events in ptg._adj_list[page_before].items():
                print(f"  Checking transition to: {page_after.id}")
                
                # If target page is not visited, execute events to reach target page and visit recursively
                if page_after.id not in visited_pages_id:
                    print(f"    Executing events to reach page_after...")
                    new_event = None
                    result, error_type, current_page = verify_event_with_llm(page_before, page_after, events, device)
                    if result:
                        print(f"    Event verification passed: Successfully reached page_after")
                    else:                        
                        print(f"    Event verification failed: {error_type}")
                        if error_type == "wrong_page":
                            return_event_command = generate_return_event_command(page_before, current_page, events)
                            execute_event_command(return_event_command, current_page, device)
                        while True:
                            next_event_command = generate_next_event_command(page_before, page_after)
                            new_event = execute_event_command(next_event_command, page_before, device)
                            result, error_type, current_page = verify_event_with_llm(page_before, page_after, events, device)
                            if result:
                                break
                            else:
                                if error_type == "wrong_page":
                                    return_event_command = generate_return_event_command(page_before, current_page, events)
                                    execute_event_command(return_event_command, current_page, device)
                    if new_event:
                        ptg._adj_list[page_before][page_after] = [new_event]
                        current_page_after = device.dump_page(refresh=True)
                        page_after.img = current_page_after.img
                        page_after.vht = current_page_after.vht
                        page_after.info = current_page_after.info
                    dfs_verify(page_after) 
                else:
                    print(f"    Page {page_after.info.ability} already visited, skipping")
        
        return True
    

    def verify_event_with_llm(page_before, page_after, events, device):
        print("=====================event verify===========================")
        device.execute(events)
        time.sleep(3)
        current_page = device.dump_page(refresh=True)
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
        response_content = response.content.strip()
        
        if response_content.startswith('```'):
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_content, re.DOTALL)
            if match:
                response_content = match.group(1).strip()
        
        result_json = json.loads(response_content)
        think = result_json.get("think", "")
        result = result_json.get("result", False)
        error_type = result_json.get("error_type", "")
        
        print(f"Analysis process: {think}")
        print(f"Verification result: {'Pass' if result else 'Failed'}")
        print(f"Error type: {error_type}")
        return result, error_type, current_page

        
    def generate_return_event_command(page_before, current_page, events):
        print("=====================generate return event command===========================")
        messages = [
            SystemMessage(content=generate_return_operation_prompt),
            HumanMessage(content=[
                {"type": "text", "text": "First image: target page (the page we want to return to, the page before the action is executed)"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(page_before.img)}"}},
                {"type": "text", "text": "Second image: the event to be executed"},
                # TODO: needs optimization, events is a list, needs to be converted to string
                {"type": "text", "text": f"{events}"},
                {"type": "text", "text": "Third image: current page (the page after the action is executed, need to return to the target page)"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(current_page.img)}"}},
            ]),
        ]
        response = llm.invoke(messages)
        print(f"Generated return operation command: {response.content}")
        return response.content


    def generate_next_event_command(page_before, page_after):
        print("=====================generate next event command===========================")
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
        print(f"Generated next operation command: {response.content}")
        return response.content
    
    def execute_event_command(command, page, device):
        print("=====================execute event command===========================")        
        messages = [
            SystemMessage(content=event_llm_prompt),
            HumanMessage(content=[
                {"type": "text", "text": command},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(page.img)}"}},
            ]),
        ]
        response = event_llm.invoke(messages)
        parsed_output = json.loads(parse_action_output(response.content))
        print("parsed_output: ", parsed_output)
        new_event = phone_operation(parsed_output, page.img.shape, device, page)
        return new_event

    # page = device.dump_page(refresh=True)
    # execute_event_command("在瑞幸点一杯生椰拿铁，到店取", page, device)
    # return
    
    # TODO: needs optimization
    first_page = ptg.pages[0]
    current_page = device.dump_page(refresh=True)
    first_page.img = current_page.img
    first_page.vht = current_page.vht
    first_page.info = current_page.info
    print(f"starting DFS from first page: {first_page.id}")
    if not dfs_verify(first_page):
        return False
    
    print("PTG verification completed!")
    return True

# Keep original function as simple verification method
# def verify_ptg_simple(ptg):
#     """
#     Simple PTG verification method (original implementation)
#     """
#     for src_page, tgt_page in ptg._adj_list.items():
#         for tgt_page, events in tgt_page.items():
#             for event in events:
#                 if not is_node_exist(src_page, event):
#                     print(f"event not exist: {event}")
#                     return False
#             print(f"event exist: {event}")
#     return True

def extract_node_by_coordinates(click_x, click_y, page):
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
    start_abs = coordinates_convert(parsed_output["start_box"], (shape[1], shape[0])) if parsed_output["start_box"] else None
    end_abs = coordinates_convert(parsed_output["end_box"], (shape[1], shape[0])) if parsed_output["end_box"] else None
    direction = parsed_output["direction"] if parsed_output["direction"] else None

    if parsed_output["action"] == "click" and start_abs:
        center_pos = (
            (start_abs[0] + start_abs[2]) // 2,
            (start_abs[1] + start_abs[3]) // 2
        )
        print(f"Click coordinates: {center_pos}")
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
    