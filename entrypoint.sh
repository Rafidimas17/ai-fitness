#!/bin/bash

# Jalankan dua skrip Python secara bersamaan
python3 model.py &
python3 traffic.py &

# Tunggu kedua proses selesai
wait
