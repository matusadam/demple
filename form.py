import json

s = json.loads(open("netmsgframe_struct.json").read())

new = {'NetMsgFrame':dict()}
offset = 0
for field in s:
    name = field[0]
    type = field[1]
    new['NetMsgFrame'][name] = {
        't' : type,
        'offset' : offset
    }
    match type:
        case "B":
            offset += 1
            size = 1
        case "b":
            offset += 1
            size = 1
        case "h":
            offset += 2
            size = 2
        case "H":
            offset += 2
            size = 2
        case "i":
            offset += 4
            size = 4
        case "f":
            offset += 4
            size = 4
        case _:
            # variable len String 
            typelen = int(type[:-1])
            offset += typelen
            size = typelen
    new['NetMsgFrame'][name]['size'] = size


print(new)

with open("structs.json", "w") as f:
    f.write(json.dumps(new, indent=4))