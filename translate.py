import json

  

def transform(data):
    res = ""
    dict_data = json.loads(data)
    if 'result' in dict_data:
        res = dict_data['text']
    return res

def transcript(data):
    res = ""
    dict_data = json.loads(data)
    if 'partial' in dict_data:
        res = dict_data['partial']
    elif 'result' in dict_data:
        res = dict_data['text']
    
    return res

