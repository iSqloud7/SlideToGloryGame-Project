HOST:
Terminal 1:
python main.py
3
Terminal 2:
python main.py
4
Terminal 3:
ngrok start --all
---> on browser, copy & paste both links into game_client.py to AUTH_SERVER & WEBSOCKET_SERVER
Terminal 4:
python main.py
2

CLIENT:
---> both links to set into game_client.py to AUTH_SERVER & WEBSOCKET_SERVER
Terminal 1:
python main.py
2

===========
ngrok setup
===========

1.  Register & Log in: https://dashboard.ngrok.com/signup.
2.  https://dashboard.ngrok.com/get-started/your-authtoken -> Copy authtoken.
3.  Ngrok config add-authtoken <YOUR_AUTHTOKEN> -> Install authtoken in computer using Windows PoweShell.
4.  Authtoken is in this location: C:\Users\<User>\.ngrok2\ngrok.yml.
5.  Add this into ngrok.yml:
tunnels:
  auth_server:
    proto: http
    addr: 8000
  websocket_server:
    proto: http
    addr: 8765
6. Run all of that with: ngrok start --all.


