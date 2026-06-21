import json
with open(r'D:\网申助手\docs\network_trace.har', 'r', encoding='utf-8') as f:
    data = json.load(f)
log = data['log']
pages = log.get('pages', [])
entries = log.get('entries', [])
print(f"Pages: {len(pages)}")
print(f"Entries (requests): {len(entries)}")
print()
print("Pages captured:")
for p in pages:
    print(f"  {p['title']}")
print()
urls = set()
for e in entries:
    url = e.get('request', {}).get('url', '')
    if 'saucedemo' in url:
        urls.add(url.split('?')[0])
print(f"Unique saucedemo URLs: {len(urls)}")
for u in sorted(urls):
    print(f"  {u}")
