class DvoiceError(Exception):
    pass

class SourceNotFoundError(DvoiceError):
    pass

class EngineNotFoundError(DvoiceError):
    pass

class ModelNotFoundError(DvoiceError):
    pass

class OutputExistsError(DvoiceError):
    pass

class TranscriptionError(DvoiceError):
    pass

class AudioExtractionError(DvoiceError):
    pass
