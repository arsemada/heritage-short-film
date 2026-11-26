"""Errors the pipeline can report without hiding the cause."""


class PipelineError(Exception):
    """Base error for problems a person running the pipeline can act on."""


class StoryboardError(PipelineError):
    """The storyboard or the approved story text failed validation."""


class CredentialsError(PipelineError):
    """A required API key is missing. No provider request was sent."""


class TransientProviderError(PipelineError):
    """A provider failed in a way that waiting and retrying might fix."""

    def __init__(self, message: str, *, retry_after_sec: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_sec = retry_after_sec


class PermanentProviderError(PipelineError):
    """A provider failed in a way that retrying the same request will not fix."""


class MissingFFmpegError(PipelineError):
    """Narration was measured, but FFmpeg is not available to make the radio cut."""

    def __init__(self, spoken_duration_sec: float) -> None:
        self.spoken_duration_sec = spoken_duration_sec
        super().__init__(
            "FFmpeg was not found on PATH, so outputs/radio_cut.mp4 was not written. "
            "Install FFmpeg and run python -m pipeline radio-cut again."
        )
