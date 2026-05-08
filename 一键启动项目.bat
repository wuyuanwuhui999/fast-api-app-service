source .venv/bin/activate
python -m uvicorn user.main:app --reload --port 4005 --host 0.0.0.0
python -m uvicorn chat.main:app --reload --port 4006 --host 0.0.0.0
python -m uvicorn tenant.main:app --reload --port 4007 --host 0.0.0.0
python -m uvicorn prompt.main:app --reload --port 4008 --host 0.0.0.0
pause