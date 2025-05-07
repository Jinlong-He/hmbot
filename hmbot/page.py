class Page(object):
    def __init__(self, name='', vht=None, img=None, ability='', bundle='', **resource):
        self.name = name
        self.vht = vht
        self.img = img
        self.ability = ability
        self.bundle = bundle
        self.resource = {**resource}
        
    
    def _is_same(self, page):
        #todo
        return False
    
    def all(self, **attrib):
        return self.vht.all(attrib)
    