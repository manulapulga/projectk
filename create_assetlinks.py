import json
import os

# Create directory
os.makedirs(".well-known", exist_ok=True)

# Create data
data = [{
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
        "namespace": "android_app",
        "package_name": "app.litmusq.android",
        "sha256_cert_fingerprints": [
            "A4702D5462EC3F8E951A0174AAA2A44EF76518148CEEA9BC9590D46907E20B36"
        ]
    }
}]

# Write to file
with open(".well-known/assetlinks.json", "w") as f:
    json.dump(data, f, indent=2)

print("✅ Created .well-known/assetlinks.json")