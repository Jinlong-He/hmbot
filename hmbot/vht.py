import xml.etree.ElementTree as ET
from .exception import*
import json, re

class VHT(object):
    """
    The class describes a view hierarchy tree
    """
    def __init__(self, root=None, compressed=True):
        self._root = root
        if compressed:
            self._compress(self._root)

    def __str__(self):
        return str(self._root._dict())
    
    def __call__(self, **kwds):
        return self._root(kwds)

    def roots(self):
        return self.__call__(type='root')
    
    def _compress(self, node):
        if len(node._children) == 1 and node.attribute['bounds'] == node._children[0].attribute['bounds']:
            node._compress(node._children[0])
            node._children = node._children[0]._children
            self._compress(node)
        else:
            for child in node._children:
                self._compress(child)
    

class VHTNode(object):
    """
    The class describes a node of view hierarchy tree
    """
    def __init__(self, attrib={}, **extra):
        if not isinstance(attrib, dict):
            raise TypeError("attrib must be dict, not %s" % (attrib.__class__.__name__,))
        self.attribute = {**attrib, **extra}
        self._children = []

    def __str__(self):
        return str(self.attribute)
    
    def __len__(self):
        return len(self._children)
    
    def __getitem__(self, index):
        return self._children[index]
    
    def __setitem__(self, index, node):
        if isinstance(index, slice):
            for child in node:
                self._assert_is_node(child)
        else:
            self._assert_is_node(node)
        self._children[index] = node
    
    def __delitem__(self, index):
        del self._children[index]
    
    def __call__(self, **kwds):
        nodes = []
        if self._satisfy(kwds):
            nodes.append(self)
        for child in self._children:
            nodes.extend(child(**kwds))
        return nodes
    
    def append(self, node):
        self._assert_is_node(node)
        self._children.append(node)
    
    def extend(self, nodes):
        for node in nodes:
            self._assert_is_node(node)
            self._children.append(node)
    
    def _assert_is_node(self, node):
        if not isinstance(node, VHTNode):
            raise TypeError('expected a VHTNode, not %s' % type(node).__name__)

    def _dict(self):
        children_dict = [child._dict() for child in self._children]
        return {
            'attributes': self._json(),
            'children': children_dict
        }

    def _json(self):
        attribute = self.attribute
        attribute['bounds'] = ''.join([str(sublist) for sublist in self.attribute['bounds']])
        attribute['center'] = str(attribute['center'])
        return attribute
    
    def _satisfy(self, attrib):
        for key, value in attrib.items():
            if key not in self.attribute or self.attribute[key] != value:
                return False
        return True
    
    def _compress(self, node):
        for (key, value) in self.attribute.items():
             if key in ['clickable', 'longClickable', 'selected', 'checkable', 'checked']:
                if value == 'true' or node.attribute[key] == 'true':
                    self.attribute[key] = 'true'
        self.attribute['text'] += node.attribute['text']

    

class VHTParser(object):
    """
    The class describes a parser for view hierarchy tree
    """
    def __init__(self):
        pass

    @classmethod
    def parse(cls, file):
        pass
        # if isinstance(source, Element):
        #     pass
        # elif isinstance(source, dict):
        #     return VHT(VHTParser._parse_hdc_json(source))
        # # , source['children'][0]['attributes']['abilityName'], source['children'][0]['attributes']['abilityName']
        # else:
        #     raise TypeError('expected a dict or Element, not %s' % type(source).__name__)

    @classmethod
    def dump(cls, vht, file, indent=2):
        with open(file, 'w') as write_file:
            json.dump(vht._root._dict(), write_file, indent=indent, ensure_ascii=False)
    
    @classmethod
    def _parse_hdc_json(cls, source):
        root = VHTParser.__parse_hdc_json(source)
        return VHT(root)

    @classmethod
    def __parse_hdc_json(cls, source):
        if 'attributes' in source:
            extra = source['attributes']
            bound_re = '\[(\d+),(\d+)\]\[(\d+),(\d+)\]'
            match = re.match(bound_re, extra['bounds'])
            if match:
                (x1, y1, x2, y2) = map(int, match.groups())
            else: 
                raise BoundsError('%s is not in form [x1,y1][x2,y2]' % extra['bounds'])
            attrib = {'bundle': '', 'page': ''}
            if 'bundleName' in extra:
                attrib['bundle'] = extra['bundleName']
                attrib['page'] = extra['pagePath']

            root = VHTNode(attrib=attrib,
                           bounds = [[x1,y1],[x2,y2]],
                           clickable = extra['clickable'],
                           longClickable = extra['longClickable'],
                           selected = extra['selected'],
                           checkable = extra['checkable'],
                           checked = extra['checked'],
                           type = extra['type'],
                           text = extra['text'],
                           center = [int((x1 + x2)/2), int((y1 + y2)/2)])
            if 'children' in source:
                children = source['children']
                for child in children:
                    root.append(VHTParser.__parse_hdc_json(child))
            return root
        else:
            raise JsonKeyError('expected key: attributes')

    @classmethod
    def _parse_adb_xml(cls, source):
        source = ET.fromstring(source)
        root = VHTParser.__parse_adb_xml(source)
        return VHT(root)

    @classmethod
    def __parse_adb_xml(cls, source):
        attrib = {'bundle': '', 'page': ''}
        if source.tag == 'hierarchy':
            root = VHTNode(attrib=attrib,
                           bounds = [[0,0],[0,0]],
                           clickable = '',
                           longClickable = '',
                           selected = '',
                           checkable = '',
                           checked = '',
                           type = '',
                           text = '',
                           center = [0,0])
        elif source.tag == 'node':
            extra = source.attrib
            bound_re = '\[(\d+),(\d+)\]\[(\d+),(\d+)\]'
            match = re.match(bound_re, extra['bounds'])
            if match:
                (x1, y1, x2, y2) = map(int, match.groups())
            else: 
                raise BoundsError('%s is not in form [x1,y1][x2,y2]' % extra['bounds'])
            attrib['bundle'] = extra['package']
            root = VHTNode(attrib=attrib,
                           bounds = [[x1,y1],[x2,y2]],
                           clickable = extra['clickable'],
                           longClickable = extra['long-clickable'],
                           selected = extra['selected'],
                           checkable = extra['checkable'],
                           checked = extra['checked'],
                           type = extra['class'],
                           text = extra['text'],
                           center = [int((x1 + x2)/2), int((y1 + y2)/2)])
        for child in source:
            root.append(VHTParser.__parse_adb_xml(child))
        return root