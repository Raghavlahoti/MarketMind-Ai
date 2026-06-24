import urllib.request
import os

os.makedirs('d:/MarketMind Ai/scratch/html', exist_ok=True)

urls = {
    'auth.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzQ0MDYzOGM3YTgyODQ5NjViODUyZmM1NzIwYWU0ZjQwEgsSBxDHhaba5QQYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDcxOTM3Mzk2MjcyOTY5NjkyMg&filename=&opi=96797242',
    'dashboard.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzQyMmE4MTIyYjBhYjRmZmVhMTBlNjY5MWM5YjY2ODJkEgsSBxDHhaba5QQYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDcxOTM3Mzk2MjcyOTY5NjkyMg&filename=&opi=96797242',
    'workspace.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzY4M2M3NzllZmE2MDQ4MGI4OGQ4MjgwY2M3NWZkZmFhEgsSBxDHhaba5QQYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDcxOTM3Mzk2MjcyOTY5NjkyMg&filename=&opi=96797242',
    'document_center.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzk1NmYzNzQwYjVjZjQ0ZmZiOWZlODE3NGFiZWM5MjE2EgsSBxDHhaba5QQYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDcxOTM3Mzk2MjcyOTY5NjkyMg&filename=&opi=96797242',
    'chat.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzM1NWM4MDU0ZGNlYzRmMmRhMzQ3ODMwMDI3N2I1ZjQzEgsSBxDHhaba5QQYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDcxOTM3Mzk2MjcyOTY5NjkyMg&filename=&opi=96797242',
    'admin.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzAwZGNkOWYxM2M5YjQ5MzA5MDU5MTQ5M2FlZTU2OTA0EgsSBxDHhaba5QQYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDcxOTM3Mzk2MjcyOTY5NjkyMg&filename=&opi=96797242',
    'settings.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzhhZjM2YTM4YTg2MDQyOGRhZGYzZWJkODIwYTllNWNiEgsSBxDHhaba5QQYAZIBJAoKcHJvamVjdF9pZBIWQhQxMDcxOTM3Mzk2MjcyOTY5NjkyMg&filename=&opi=96797242'
}

for name, url in urls.items():
    print(f"Downloading {name}...")
    try:
        urllib.request.urlretrieve(url, f"d:/MarketMind Ai/scratch/html/{name}")
        print("Success")
    except Exception as e:
        print(f"Error: {e}")
