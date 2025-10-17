import { useTranslation } from "react-i18next";
import CheckmarkIcon from "#/icons/checkmark.svg?react";
import CopyIcon from "#/icons/copy.svg?react";
import { I18nKey } from "#/i18n/declaration";

interface CopyToClipboardButtonProps {
  isHidden: boolean;
  isDisabled: boolean;
  onClick: () => void;
  mode: "copy" | "copied";
}

export function CopyToClipboardButton({
  isHidden,
  isDisabled,
  onClick,
  mode,
}: CopyToClipboardButtonProps) {
  const { t } = useTranslation();
  return (
    <button
      hidden={isHidden}
      disabled={isDisabled}
      data-testid="copy-to-clipboard"
      type="button"
      onClick={onClick}
      aria-label={t(
        mode === "copy" ? I18nKey.BUTTON$COPY : I18nKey.BUTTON$COPIED,
      )}
      className="button-base p-1 cursor-pointer bg-gray-800/50 hover:bg-gray-700/70 rounded-md backdrop-blur-sm transition-all duration-200"
    >
      {mode === "copy" && (
        <CopyIcon
          width={15}
          height={15}
          className="transition-transform duration-200"
        />
      )}
      {mode === "copied" && (
        <CheckmarkIcon
          width={15}
          height={15}
          className="text-green-500 animate-in fade-in scale-110"
        />
      )}
    </button>
  );
}
