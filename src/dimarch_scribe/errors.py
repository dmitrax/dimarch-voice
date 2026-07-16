class ScribeError(Exception):
    pass

class SourceNotFoundError(ScribeError):
    pass

class EngineNotFoundError(ScribeError):
    pass

class ModelNotFoundError(ScribeError):
    pass

class OutputExistsError(ScribeError):
    pass

class TranscriptionError(ScribeError):
    pass

class AudioExtractionError(ScribeError):
    pass
