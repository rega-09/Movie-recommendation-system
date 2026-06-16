#!/usr/bin/env python3
"""
Download required NLTK data packages.
Run once before starting the server: python setup_nltk.py
"""
import nltk
from nltk.corpus import stopwords
stopwords.words("english")
packages = ["punkt", "stopwords", "punkt_tab"]
for pkg in packages:
    print(f"Downloading NLTK package: {pkg}")
    nltk.download(pkg, quiet=False)

print("✅ NLTK setup complete.")
