from tube.utils.dd import get_edge_table, get_node_table_name, get_node_label, get_parent_name, get_parent_label, \
    get_properties_types, object_to_string, get_all_children_of_node, get_node_category
from tube.etl.indexers.injection.nodes.collecting_node import CollectingNode, RootNode, LeafNode
from ..base.parser import Parser as BaseParser
from ..base.prop import PropFactory


class Path(object):
    def __init__(self, prop_name, path_name, src):
        self.name = prop_name
        self.src = src
        self.path = Path.create_path(path_name)

    @classmethod
    def create_path(cls, s_path):
        return tuple(s_path.split('.'))

    def __key__(self):
        return (self.src,) + self.path

    def __hash__(self):
        return hash(self.__key__())

    def __str__(self):
        return object_to_string(self)

    def __repr__(self):
        return str(self.__key__())

    def __eq__(self, other):
        return self.__key__() == other.__key__()


class NodePath(object):
    def __init__(self, class_name, upper_path):
        self.class_name = class_name
        self.upper_path = upper_path

    def __str__(self):
        return object_to_string(self)

    def __repr__(self):
        return self.__str__()


class Parser(BaseParser):
    def __init__(self, mapping, model, dictionary):
        super(Parser, self).__init__(mapping, model)
        self.dictionary = dictionary
        self.props = PropFactory.create_props_from_json(self.mapping['props'])
        self.final_fields = [p for p in self.props]
        self.final_types = self.get_props_types()
        self.leaves = set([])
        self.collectors = []
        self.roots = set([])
        self.get_collecting_nodes()
        self.types = self.get_types()

    def get_first_node_label_with_category(self):
        if len(self.mapping['injecting_props'].items()) > 0:
            return None

        processing_queue = []
        children = get_all_children_of_node(self.model, self.model.Node.get_subclass(
            self.mapping['injecting_props'].keys()[0]
        ).__name__)
        for child in children:
            processing_queue.append(NodePath(child.__src_class__, child.__src_dst_assoc__))
        i = 0
        while (i < len(processing_queue)):
            current_node = processing_queue[i]
            current_label = get_node_label(self.model, current_node.class_name)
            if get_node_category(self.dictionary, current_label) == self.mapping.get('category', 'data_file'):
                return current_label
            children = get_all_children_of_node(self.model, current_node.class_name)
            for child in children:
                processing_queue.append(
                    NodePath(child.__src_class__, '.'.join([child.__src_dst_assoc__, current_node.upper_path])))
            i += 1
        return None

    def get_props_types(self):
        types = {}

        first_node = self.get_first_node_label_with_category()
        if first_node is None:
            return {}

        a = get_properties_types(self.model, first_node)
        for j in self.mapping['props']:
            name = j.get('src', j.get('name'))
            types[name] = a[name]

        types = self.select_widest_types(types)
        types['{}_id'.format(self.doc_type)] = str
        return types

    def get_collecting_nodes(self):
        for k, v in self.mapping['injecting_props'].items():
            flat_paths = self.create_collecting_paths(k)
        self.leaves, self.collectors, self.roots = self.construct_reversed_collection_tree(flat_paths)
        self.update_level()
        self.collectors.sort()

    def update_level(self):
        """
        Update the level of nodes in the parsing tree
        :return:
        """
        level = 1
        assigned_levels = set([])
        just_assigned = set([])
        for root in self.roots:
            for child in root.children:
                if len(child.children) == 0 or child in just_assigned:
                    continue
                child.level = level
                just_assigned.add(child)
        assigned_levels = assigned_levels.union(just_assigned)

        level += 1
        leaves = [c for c in self.collectors if len(c.children) == 0]
        len_non_leaves = len(self.collectors) - len(leaves)
        while len(assigned_levels) != len_non_leaves:
            new_assigned = set([])
            for collector in just_assigned:
                for child in collector.children:
                    if len(child.children) == 0 or child in assigned_levels:
                        continue
                    child.level = level
                    new_assigned.add(child)
            just_assigned = new_assigned
            assigned_levels = assigned_levels.union(new_assigned)
            level += 1

    def update_final_fields(self, root_name):
        for f in self.mapping['injecting_props'][root_name]['props']:
            src = f['src'] if 'src' in f else f['name']
            p = PropFactory.adding_prop(f['name'], src, [])
            if p.src != 'id':
                f_type = self.select_widest_type(get_properties_types(self.model, root_name)[p.src])
            else:
                f_type = str
            self.final_fields.append(p)
            self.final_types[p.name] = f_type

    def add_root_node(self, child, roots, segment):
        root_name = get_node_label(self.model, get_parent_name(self.model, child.name, segment))
        _, edge_up_tbl = get_edge_table(self.model, child.name, segment)
        root_tbl_name = get_node_table_name(self.model, get_parent_label(self.model, child.name, segment))
        top_node = roots[root_name] if root_name in roots \
            else RootNode(root_name, root_tbl_name,
                          self.mapping['injecting_props'][root_name]['props']
                          )
        if type(child) is CollectingNode:
            child.add_parent(top_node, edge_up_tbl)
        top_node.add_child(child)
        if root_name not in roots:
            self.update_final_fields(root_name)

        roots[root_name] = top_node

    def add_collecting_node(self, child, collectors, fst):
        parent_name = get_node_label(self.model, get_parent_name(self.model, child.name, fst))
        _, edge_up_tbl = get_edge_table(self.model, child.name, fst)
        collecting_node = collectors[parent_name] if parent_name in collectors \
            else CollectingNode(parent_name)
        collecting_node.add_child(child)
        child.add_parent(collecting_node, edge_up_tbl)
        collectors[parent_name] = collecting_node
        return collecting_node

    def add_leaf_node(self, name, leaves):
        leaf_tbl_name = get_node_table_name(self.model, name)

        if name not in leaves:
            leaf_node = LeafNode(name, leaf_tbl_name)
            leaves[name] = leaf_node
        return leaves[name]

    def construct_reversed_collection_tree(self, flat_paths):
        leaves = {}
        collectors = {}
        roots = {}
        for p in flat_paths:
            segments = list(p.path)
            _, edge_up_tbl = get_edge_table(self.model, p.src, segments[0])
            self.add_leaf_node(p.src, leaves)
            if p.src not in collectors:
                collectors[p.src] = CollectingNode(p.src, edge_up_tbl)
            child = collectors[p.src]
            if len(segments) > 1:
                for fst in segments[0:len(segments)-1]:
                    child = self.add_collecting_node(child, collectors, fst)
            self.add_root_node(child, roots, segments[-1])
        return leaves.values(), collectors.values(), roots.values()

    def create_collecting_paths(self, label):
        name = self.model.Node.get_subclass(label).__name__
        processing_queue = []
        flat_paths = set()
        children = get_all_children_of_node(self.model, name)
        for child in children:
            processing_queue.append(NodePath(child.__src_class__, child.__src_dst_assoc__))
        i = 0
        while (i < len(processing_queue)):
            current_node = processing_queue[i]
            current_label = get_node_label(self.model, current_node.class_name)
            if get_node_category(self.dictionary, current_label) == self.mapping.get('category', 'data_file'):
                path = Path(len(flat_paths), current_node.upper_path, current_label)
                flat_paths.add(path)
            children = get_all_children_of_node(self.model, current_node.class_name)
            for child in children:
                processing_queue.append(
                    NodePath(child.__src_class__, '.'.join([child.__src_dst_assoc__, current_node.upper_path])))
            i += 1
        return flat_paths

    def get_types(self):
        return self.final_types