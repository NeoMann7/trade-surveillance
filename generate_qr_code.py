#!/usr/bin/env python3
"""
Simple script to generate a QR code from a URL
"""

import qrcode
from PIL import Image

# The Microsoft Forms URL
url = "https://forms.office.com/pages/responsepage.aspx?id=GVfz00I_UEW1Z0QhyDyoey2E3uK1f9RPkIOcCvU0675UMlRWSFBPNTQ4WERXOEQwNU0yMU4ySENKTC4u&route=shorturl"

# Create QR code instance
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)

# Add data to QR code
qr.add_data(url)
qr.make(fit=True)

# Create image from QR code
img = qr.make_image(fill_color="black", back_color="white")

# Save the image
output_file = "microsoft_forms_qr_code.png"
img.save(output_file)

print(f"✅ QR code generated successfully!")
print(f"📁 Saved as: {output_file}")
print(f"🔗 URL encoded: {url}")

