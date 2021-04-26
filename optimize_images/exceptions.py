class OIKeyboardInterrupt(KeyboardInterrupt):
    """Exception raised when the user interrupts stops the execution using a
    keyboard interrupt (typically CTRL-C).

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message=""):
        self.message = message
        super().__init__(self.message)


class OIImagesNotFoundError(FileNotFoundError):
    """Exception raised when there were no images found.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message=""):
        self.message = message
        super().__init__(self.message)


class OIInvalidPathError(ValueError):
    """Exception raised when there were no images found.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message=""):
        self.message = message
