from pyotp import TOTP
import logging
logging.basicConfig(level=logging.DEBUG,
                format='[%(levelname)s] %(message)s',
                )
class Code:
    password = None
    label = None

    def __init__(self, secret_code):
        self.secret_code = secret_code
        self.create()

    def create(self):
        try:
            self.totp = TOTP(self.secret_code)
            self.password = self.totp.now()
        except Exception as e:
            logging.error("Canno't generate a two-factor auth code")
            logging.error(str(e))
    def update(self):
        self.password = self.totp.now()


    def get_secret_code(self):
        try:
            if self.password:
                return self.password
            else:
                raise AttributeError
        except AttributeError as e:
            logging.error("Couldn't generate the code")
            logging.error(str(e))
            return None
