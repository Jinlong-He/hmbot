from .vht import VHTNode
from .window import Window
from .event import *
import json

class WTG(object):
    def __init__(self):
        self.main_windows = []
        self.windows = []
        self._adj_list = {}
        self._visited = {}
    
    def add_main_window(self, window):
        if self.add_window(window):
            self.main_windows.append(window)
            return True
        return False

    def add_window(self, window):
        if self._is_new_window(window):
            self.windows.append(window)
            self._adj_list[window] = {}
            return True
        return False
    
    def add_edge(self, src_window, tgt_window, events):
        self.add_window(src_window)
        self.add_window(tgt_window)
        self._adj_list[src_window][tgt_window] = events
    
    def _is_new_window(self, new_window):
        for window in self.windows:
            if window._is_same(new_window):
                return False
        return True
    
    def _json_list(self, dir_path):
        res = []
        for id in range(len(self.windows)):
            src_window = self.windows[id]
            vht_file, img_file = src_window._dump(id, dir_path)
            edge_list = []
            for (tgt_window, events) in self._adj_list[src_window].items():
                tgt_id = self.windows.index(tgt_window)
                event_list = [event._json() for event in events]
                edge_dict = {'target_id': tgt_id,
                             'events': event_list}
                edge_list.append(edge_dict)
            src_window_dict = src_window._dict(vht_file, img_file)
            src_window_dict['id'] = id
            res.append({'info': src_window_dict, 
                        'edge': edge_list})
        return res

class WTGParser(object):
    def parse(self, file):
        with open(file, 'r') as f:
            json_data = json.load(f)
        wtg = WTG()

        windows = []
        for item in json_data:
            window_info = item['info']
            vht = window_info['vht']
            img = window_info['img']
            rsc = window_info['rsc']
            ability = window_info['ability']
            bundle = window_info['bundle']
            window = Window(vht, img, rsc, ability, bundle)
            wtg.add_window(window)
            windows.append(window)

        for src_id, item in enumerate(json_data):
            src_window = windows[src_id]
            for edge in item['edge']:
                tgt_id = edge['target_id']
                tgt_window = windows[tgt_id]
                events = []
                for event_data in edge['events']:
                    event = None
                    type = event_data['type']
                    if type in ['Click']:
                        center = json.loads(event_data['node']['center'])
                        attrib = {
                            "center": center
                        }
                        node = VHTNode(None, attrib)
                        event = ClickEvent(node)
                    elif type in ['LongClick']:
                        center = json.loads(event_data['node']['center'])
                        attrib = {
                            "center": center
                        }
                        node = VHTNode(None, attrib)
                        event = LongClickEvent(node)
                    elif type in ['Input']:
                        center = json.loads(event_data['node']['center'])
                        attrib = {
                            "center": center
                        }
                        node = VHTNode(None, attrib)
                        text = event_data['node']['text']
                        event = InputEvent(node, text)
                    elif type in ['SwipeExt']:
                        event = SwipeExtEvent(None, None, event_data['direction'])
                    elif type in ['Key']:
                        event = KeyEvent(None, None, event_data['key'])
                    elif type in ['StartApp']:
                        event = StartAppEvent(None, event_data['app'])
                    if event:
                        events.append(event)
                wtg._adj_list[src_window][tgt_window] = events
        return wtg

    @classmethod
    def dump(cls, wtg, dir_path, indent=2):
        with open(dir_path + 'wtg.json', 'w') as write_file:
            json.dump(wtg._json_list(dir_path), write_file, indent=indent, ensure_ascii=False)

