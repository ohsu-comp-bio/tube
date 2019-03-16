from tube.etl.indexers.base.lambdas import get_aggregation_func_by_name, get_single_frame_zero_by_func, \
                            get_single_frame_value


def get_frame_zero(reducers):
    return tuple([get_single_frame_zero_by_func(rd.fn, rd.prop.id) for rd in reducers if not rd.done])


def get_normal_frame(reducers):
    """
    Create a tuple for every value, this tuple include (func-name, output_field_name, value).
    It helps spark workers know directly what to do when reading the dataframe
    :param reducers:
    :return:
    """
    return lambda x: tuple([(rd.fn, rd.prop.id, get_single_frame_value(rd.fn, x.get(rd.prop.id)))
                            for rd in reducers if not rd.done])


def seq_aggregate_with_reducer(x, y):
    """
    Sequencing function that works with the dataframe created by get_normal_frame
    :param x:
    :param y:
    :return:
    """
    res = []
    for i in range(0, len(x)):
        res.append((x[i][0], x[i][1], get_aggregation_func_by_name(x[i][0])(x[i][2], y[i][2])))
    return tuple(res)


def merge_aggregate_with_reducer(x, y):
    res = []
    for i in range(0, len(x)):
        res.append((x[i][0], x[i][1], get_aggregation_func_by_name(x[i][0], True)(x[i][2], y[i][2])))
    return tuple(res)


def intermediate_frame(prop):
    # Generalize later base on the input
    return lambda x: (('sum', prop.id, x),)
