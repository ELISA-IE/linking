import requests


if __name__ == '__main__':
    url = 'http://blender02.cs.rpi.edu:3301/linking'
    payloads = [
        {'mention': 'rpi', 'lang': 'en'},
        {'mention': '中国', 'lang': 'zh'},
        {'mention': 'España', 'lang': 'es'},
    ]
    for i in payloads:
        r = requests.get(url, params=i)
        print(r.status_code)
        print(r.text)

    url = 'http://blender02.cs.rpi.edu:3301/linking_bio'
    pdata = 'tmp/CMN_DF_000020_20140219_G00A0BX20.bio'
    data = open(pdata).read()
    payload = {'bio_str': data, 'lang': 'zh'}
    r = requests.post(url, data=payload)
    print(r.status_code)
    print(r.text)

    url = 'http://blender02.cs.rpi.edu:3301/linking_amr'
    pdata = 'tmp/amr'
    data = open(pdata).read()
    payload = {'amr_str': data}
    r = requests.post(url, data=payload)
    print(r.status_code)
    print(r.text)
