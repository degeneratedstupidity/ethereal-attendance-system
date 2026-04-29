import urllib.request
import json
import os
import random

url = 'http://127.0.0.1:8000/api/v1/users/'

# Generate a random email to avoid duplicate key errors if you run this multiple times
rand_num = random.randint(100, 999)
data = json.dumps({
    'email': f'teacher{rand_num}@college.edu',
    'password': 'password123',
    'first_name': 'Jane',
    'last_name': 'Smith',
    'role': 'teacher'
}).encode('utf-8')

req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

print("Connecting to local backend to create a teacher user...")

try:
    with urllib.request.urlopen(req) as res:
        response_data = json.loads(res.read())
        teacher_id = response_data['id']
        print(f"✅ Successfully created teacher! ID: {teacher_id}")
        
        # Locate the frontend file
        frontend_file = '../attendance-frontend/src/components/AttendanceEntry.tsx'
        if os.path.exists(frontend_file):
            with open(frontend_file, 'r') as f:
                content = f.read()
            
            # Replace the dummy ID with the real one
            if "00000000-0000-0000-0000-000000000000" in content:
                new_content = content.replace("00000000-0000-0000-0000-000000000000", teacher_id)
                with open(frontend_file, 'w') as f:
                    f.write(new_content)
                print(f"✅ Automatically updated AttendanceEntry.tsx with your new Teacher ID!")
            elif teacher_id in content:
                print("✅ AttendanceEntry.tsx already has this Teacher ID.")
            else:
                print("⚠️ ID has already been modified in AttendanceEntry.tsx. Please update it manually to:", teacher_id)
        else:
            print(f"⚠️ Could not find frontend file at {frontend_file}. Please update it manually.")

except urllib.error.HTTPError as e:
    error_message = e.read().decode('utf-8')
    print(f"❌ Backend returned an error: {e.code} - {error_message}")
except Exception as e:
    print(f"❌ Failed to connect: {e}")
