import irc.bot
import requests

class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, client_id, token, channel):
        self.client_id = "0vg1kmlbt52sp3szxv15zzlel3k1kz"
        self.token = "dhtp9v5bbefw9vmxwqn9wuwo2m6rtg"
        self.channel = '#' + "atlien_ke"
        self.username = "ATLien_Ke"

        # Get the channel id, we will need this for Helix API calls
        url = 'https://api.twitch.tv/helix/users?login=' + self.username
        headers = {
            'Client-ID': self.client_id,
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/json'
        }
        r = requests.get(url, headers=headers).json()
        print(r)
        self.channel_id = r['data'][0]['id']

        # Create IRC bot connection
        server = 'irc.chat.twitch.tv'
        port = 6697
        print ('Connecting to ' + server + ' on port ' + str(port) + '...')
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:' + self.token)], self.username, self.username)
    
    def on_welcome(self, c, e):
        print('Welcome message received')
        print('Joining ' + self.channel)

        # You must request specific capabilities before you can use them
        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.join(self.channel)


    def on_pubmsg(self, c, e):
        # If a chat message starts with an exclamation point, try to run it as a command
        if e.arguments[0][:1] == '!':
            cmd = e.arguments[0].split(' ')[0][1:]
            print ('Received command: ' + cmd)
            self.do_command(e, cmd)
        return

    def do_command(self, e, cmd):
        c = self.connection

        # Poll the API to get current game.
        if cmd == "game":
            url = 'https://api.twitch.tv/helix/channels?broadcaster_id=' + self.channel_id
            headers = {'Client-ID': self.client_id, 'Authorization': 'Bearer ' + self.token, 'Accept': 'application/json'}
            r = requests.get(url, headers=headers).json()
            c.privmsg(self.channel, self.username + ' is currently playing ' + r['data'][0]['game_name'])

        # Poll the API the get the current status of the stream
        elif cmd == "title":
            url = 'https://api.twitch.tv/helix/channels?broadcaster_id=' + self.channel_id
            headers = {'Client-ID': self.client_id, 'Authorization': 'Bearer ' + self.token, 'Accept': 'application/json'}
            r = requests.get(url, headers=headers).json()
            c.privmsg(self.channel, self.username + ' channel title is currently ' + r['data'][0]['title'])

        # Provide basic information to viewers for specific commands
        elif cmd == "raffle":
            message = "This is an example bot, replace this text with your raffle text."
            c.privmsg(self.channel, message)
        elif cmd == "schedule":
            message = "This is an example bot, replace this text with your schedule text."            
            c.privmsg(self.channel, message)

        # The command was not recognized
        else:
            c.privmsg(self.channel, "Did not understand command: " + cmd)

def main():

    username  = "ATLien_Ke"
    client_id = "0vg1kmlbt52sp3szxv15zzlel3k1kz"
    token     = "dhtp9v5bbefw9vmxwqn9wuwo2m6rtg"
    channel   = "atlien_ke"

    bot = TwitchBot(username, client_id, token, channel)
    bot.start()

if __name__ == "__main__":
    main()
