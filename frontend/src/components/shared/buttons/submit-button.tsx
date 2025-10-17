import { useTranslation } from "react-i18next";
import ArrowSendIcon from "#/icons/arrow-send.svg?react";
import { I18nKey } from "#/i18n/declaration";

interface SubmitButtonProps {
  isDisabled?: boolean;
  onClick: () => void;
}

export function SubmitButton({ isDisabled, onClick }: SubmitButtonProps) {
  const { t } = useTranslation();
  return (
    <button
      aria-label={t(I18nKey.BUTTON$SEND)}
      disabled={isDisabled}
      onClick={onClick}
      type="submit"
      className="border border-white rounded-lg w-6 h-6 hover:bg-gradient-to-br hover:from-blue-600 hover:to-blue-700 hover:border-blue-500 focus:bg-gradient-to-br focus:from-blue-600 focus:to-blue-700 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center cursor-pointer transition-all duration-200 ease-in-out hover:scale-110 active:scale-95 hover:shadow-lg hover:shadow-blue-500/50"
    >
      <ArrowSendIcon className="transition-transform duration-200" />
    </button>
  );
}
