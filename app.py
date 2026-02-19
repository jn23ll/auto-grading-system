import streamlit as st
import cv2
import numpy as np
import os
import psycopg2
import torch
import pandas as pd
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# ⭐ import database
from database import init_db, connect_db

# ⭐ สร้าง Table อัตโนมัติเมื่อเปิดแอป
init_db()
