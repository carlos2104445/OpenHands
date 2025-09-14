import json
import re
import traceback
from dataclasses import dataclass, field
from typing import Any, Self

from pydantic import BaseModel

from openhands.core.logger import openhands_logger as logger
from openhands.core.schema import ObservationType
from openhands.events.observation.observation import Observation

CMD_OUTPUT_PS1_BEGIN = '\n###PS1JSON###\n'
CMD_OUTPUT_PS1_END = '\n###PS1END###'
CMD_OUTPUT_METADATA_PS1_REGEX = re.compile(
    f'^{CMD_OUTPUT_PS1_BEGIN.strip()}(.*?){CMD_OUTPUT_PS1_END.strip()}',
    re.DOTALL | re.MULTILINE,
)

# Default max size for command output content
# to prevent too large observations from being saved in the stream
# This matches the default max_message_chars in LLMConfig
MAX_CMD_OUTPUT_SIZE: int = 30000


class CmdOutputMetadata(BaseModel):
    """Additional metadata captured from PS1."""

    exit_code: int = -1
    pid: int = -1
    username: str | None = None
    hostname: str | None = None
    working_dir: str | None = None
    py_interpreter_path: str | None = None
    prefix: str = ''  # Prefix to add to command output
    suffix: str = ''  # Suffix to add to command output

    @classmethod
    def to_ps1_prompt(cls) -> str:
        """Convert the required metadata into a PS1 prompt."""
        prompt = CMD_OUTPUT_PS1_BEGIN
        json_template = '''{
  "pid": "${!:-null}",
  "exit_code": "${?:-null}",
  "username": "\\u",
  "hostname": "\\h",
  "working_dir": "$(pwd)",
  "py_interpreter_path": "$(which python 2>/dev/null || echo null)"
}'''
        prompt += json_template
        prompt += CMD_OUTPUT_PS1_END + '\n'  # Ensure there's a newline at the end
        return prompt

    @classmethod
    def matches_ps1_metadata(cls, string: str) -> list[re.Match[str]]:
        matches = []
        for match in CMD_OUTPUT_METADATA_PS1_REGEX.finditer(string):
            json_str = match.group(1).strip()
            try:
                json.loads(json_str)
                matches.append(match)
            except json.JSONDecodeError:
                if any(var in json_str for var in ['$!', '$?', '\\u', '\\h', '$(pwd)', '$(which']):
                    logger.debug(f'Skipping PS1 template (not expanded): {json_str[:100]}...')
                    continue
                else:
                    try:
                        fixed_json = cls._fix_malformed_ps1_json(json_str)
                        if fixed_json:
                            json.loads(fixed_json)
                            matches.append(match)
                            logger.debug(f'Successfully fixed malformed PS1 JSON: {json_str[:50]}...')
                        else:
                            logger.warning(f'Could not fix malformed PS1 JSON: {json_str}. Skipping.')
                            continue
                    except json.JSONDecodeError:
                        logger.warning(
                            f'Failed to parse PS1 metadata: {json_str}. Skipping.'
                            + traceback.format_exc()
                        )
                        continue
        return matches

    @classmethod
    def _fix_malformed_ps1_json(cls, json_str: str) -> str | None:
        """Fix common JSON formatting issues from shell expansion."""
        try:
            lines = json_str.strip().split('\n')
            if not lines[0].strip().startswith('{') or not lines[-1].strip().endswith('}'):
                return None
            
            fixed_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped in ['{', '}']:
                    fixed_lines.append(line)
                elif ':' in stripped:
                    indent = line[:len(line) - len(line.lstrip())]
                    parts = stripped.split(':', 1)
                    if len(parts) == 2:
                        prop = parts[0].strip()
                        value = parts[1].strip().rstrip(',')
                        has_comma = parts[1].strip().endswith(',')
                        
                        if not (prop.startswith('"') and prop.endswith('"')):
                            prop = f'"{prop}"'
                        
                        if value == 'null' or value.isdigit() or (value.startswith('"') and value.endswith('"')):
                            quoted_value = value
                        else:
                            quoted_value = f'"{value}"'
                        
                        comma = ',' if has_comma else ''
                        fixed_lines.append(f'{indent}{prop}: {quoted_value}{comma}')
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            
            return '\n'.join(fixed_lines)
        except Exception:
            return None

    @classmethod
    def from_ps1_match(cls, match: re.Match[str]) -> Self:
        """Extract the required metadata from a PS1 prompt."""
        json_str = match.group(1).strip()
        try:
            metadata = json.loads(json_str)
        except json.JSONDecodeError:
            fixed_json = cls._fix_malformed_ps1_json(json_str)
            if fixed_json:
                metadata = json.loads(fixed_json)
            else:
                raise ValueError(f'Could not parse PS1 metadata: {json_str}')
        
        # Create a copy of metadata to avoid modifying the original
        processed = metadata.copy()
        # Convert numeric fields
        if 'pid' in metadata:
            try:
                processed['pid'] = int(float(str(metadata['pid'])))
            except (ValueError, TypeError):
                processed['pid'] = -1
        if 'exit_code' in metadata:
            try:
                processed['exit_code'] = int(float(str(metadata['exit_code'])))
            except (ValueError, TypeError):
                logger.warning(
                    f'Failed to parse exit code: {metadata["exit_code"]}. Setting to -1.'
                )
                processed['exit_code'] = -1
        return cls(**processed)


@dataclass
class CmdOutputObservation(Observation):
    """This data class represents the output of a command."""

    command: str
    observation: str = ObservationType.RUN
    # Additional metadata captured from PS1
    metadata: CmdOutputMetadata = field(default_factory=CmdOutputMetadata)
    # Whether the command output should be hidden from the user
    hidden: bool = False

    def __init__(
        self,
        content: str,
        command: str,
        observation: str = ObservationType.RUN,
        metadata: dict[str, Any] | CmdOutputMetadata | None = None,
        hidden: bool = False,
        **kwargs: Any,
    ) -> None:
        # Truncate content before passing it to parent
        # Hidden commands don't go through LLM/event stream, so no need to truncate
        truncate = not hidden
        if truncate:
            content = self._maybe_truncate(content)

        super().__init__(content)

        self.command = command
        self.observation = observation
        self.hidden = hidden
        if isinstance(metadata, dict):
            self.metadata = CmdOutputMetadata(**metadata)
        else:
            self.metadata = metadata or CmdOutputMetadata()

        # Handle legacy attribute
        if 'exit_code' in kwargs:
            self.metadata.exit_code = kwargs['exit_code']
        if 'command_id' in kwargs:
            self.metadata.pid = kwargs['command_id']

    @staticmethod
    def _maybe_truncate(content: str, max_size: int = MAX_CMD_OUTPUT_SIZE) -> str:
        """Truncate the content if it's too large.

        This helps avoid storing unnecessarily large content in the event stream.

        Args:
            content: The content to truncate
            max_size: Maximum size before truncation. Defaults to MAX_CMD_OUTPUT_SIZE.

        Returns:
            Original content if not too large, or truncated content otherwise
        """
        if len(content) <= max_size:
            return content

        # Truncate the middle and include a message about it
        half = max_size // 2
        original_length = len(content)
        truncated = (
            content[:half]
            + '\n[... Observation truncated due to length ...]\n'
            + content[-half:]
        )
        logger.debug(
            f'Truncated large command output: {original_length} -> {len(truncated)} chars'
        )
        return truncated

    @property
    def command_id(self) -> int:
        return self.metadata.pid

    @property
    def exit_code(self) -> int:
        return self.metadata.exit_code

    @property
    def error(self) -> bool:
        return self.exit_code != 0

    @property
    def message(self) -> str:
        return f'Command `{self.command}` executed with exit code {self.exit_code}.'

    @property
    def success(self) -> bool:
        return not self.error

    def __str__(self) -> str:
        return (
            f'**CmdOutputObservation (source={self.source}, exit code={self.exit_code}, '
            f'metadata={json.dumps(self.metadata.model_dump(), indent=2)})**\n'
            '--BEGIN AGENT OBSERVATION--\n'
            f'{self.to_agent_observation()}\n'
            '--END AGENT OBSERVATION--'
        )

    def to_agent_observation(self) -> str:
        ret = f'{self.metadata.prefix}{self.content}{self.metadata.suffix}'
        if self.metadata.working_dir:
            ret += f'\n[Current working directory: {self.metadata.working_dir}]'
        if self.metadata.py_interpreter_path:
            ret += f'\n[Python interpreter: {self.metadata.py_interpreter_path}]'
        if self.metadata.exit_code != -1:
            ret += f'\n[Command finished with exit code {self.metadata.exit_code}]'
        return ret


@dataclass
class IPythonRunCellObservation(Observation):
    """This data class represents the output of a IPythonRunCellAction."""

    code: str
    observation: str = ObservationType.RUN_IPYTHON
    image_urls: list[str] | None = None

    @property
    def error(self) -> bool:
        return False  # IPython cells do not return exit codes

    @property
    def message(self) -> str:
        return 'Code executed in IPython cell.'

    @property
    def success(self) -> bool:
        return True  # IPython cells are always considered successful

    def __str__(self) -> str:
        result = f'**IPythonRunCellObservation**\n{self.content}'
        if self.image_urls:
            result += f'\nImages: {len(self.image_urls)}'
        return result
