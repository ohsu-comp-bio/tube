from tube.utils.dd import object_to_string


class PropFactory(object):
    list_props = []
    prop_by_names = {}

    @staticmethod
    def get_length():
        return len(PropFactory.list_props)

    @staticmethod
    def create_value_mappings(value_mappings_in_json):
        res = []
        for item in value_mappings_in_json:
            k = item.keys()[0]
            res.append(ValueMapping(k, item[k]))
        return res

    @staticmethod
    def adding_prop(name, src, value_mappings, fn=None):
        prop = PropFactory.prop_by_names.get(name)
        if prop is None:
            prop = Prop(PropFactory.get_length(), name, src, PropFactory.create_value_mappings(value_mappings), fn)
            PropFactory.list_props.append(prop)
            PropFactory.prop_by_names[name] = prop
        return prop

    @staticmethod
    def create_prop_from_json(p):
        value_mappings = p.get('value_mappings', [])
        src = p['src'] if 'src' in p else p['name']
        fn = p.get('fn')
        return PropFactory.adding_prop(p['name'], src, value_mappings, fn)

    @staticmethod
    def get_prop_by_id(id):
        return PropFactory.list_props[id]

    @staticmethod
    def get_prop_by_name(name):
        return PropFactory.prop_by_names[name]

    @staticmethod
    def get_prop_by_json(p):
        return PropFactory.get_prop_by_name(p['name'])

    @staticmethod
    def create_props_from_json(props_in_json):
        res = []
        for p in props_in_json:
            res.append(PropFactory.create_prop_from_json(p))
        return res


class ValueMapping(object):
    def __init__(self, original, final):
        self.original = original
        self.final = final


class Prop(object):
    def __init__(self, id, name, src, value_mappings, fn=None):
        self.id = id
        self.name = name
        self.src = src
        self.value_mappings = [] if value_mappings is None else value_mappings
        self.fn = fn

    def __hash__(self):
        return self.id

    def __str__(self):
        return object_to_string(self)

    def __repr__(self):
        return self.__str__()
