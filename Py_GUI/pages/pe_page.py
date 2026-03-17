from pages.base_functions import BaseDAQPage


class PEPage(BaseDAQPage):

    def __init__(self, receiver, sender):

        super().__init__(receiver, sender)

        # nothing extra needed for PE