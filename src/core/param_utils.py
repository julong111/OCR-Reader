# src/core/param_utils.py

def serialize_rect_list(rect_list):
    if not rect_list:
        return ""
    return ';'.join([','.join(map(str, rect)) for rect in rect_list])

def deserialize_rect_list(rect_str):
    if not rect_str:
        return []
    rect_list = []
    for part in rect_str.split(';'):
        try:
            coords = [int(x.strip()) for x in part.split(',')]
            if len(coords) == 4:
                rect_list.append(coords)
        except (ValueError, IndexError):
            continue
    return rect_list

def serialize_point_list(point_list):

    if not point_list:
        return ""
    return ';'.join([','.join(map(str, point)) for point in point_list])

def deserialize_point_list(point_str):

    if not point_str:
        return []
    point_list = []
    for part in point_str.split(';'):
        try:
            coords = [int(x.strip()) for x in part.split(',')]
            if len(coords) == 2:
                point_list.append(coords)
        except (ValueError, IndexError):
            continue
    return point_list
