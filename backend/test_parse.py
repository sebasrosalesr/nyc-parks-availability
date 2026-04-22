from datetime import datetime
s = "3/17/2026 6:30 p.m."
cl = s.replace("p.m.", "PM").replace("a.m.", "AM").replace(".", "")
print(cl)
dt = datetime.strptime(cl, "%m/%d/%Y %I:%M %p")
print(dt)
