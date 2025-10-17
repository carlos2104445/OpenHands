import { useTranslation } from "react-i18next";
import { Typography } from "#/ui/typography";

export function HomeHeaderTitle() {
  const { t } = useTranslation();

  return (
    <div className="h-[80px] flex items-center">
      <Typography.H1 className="bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 bg-clip-text text-transparent animate-in fade-in slide-in-from-top-4 duration-700">
        {t("HOME$LETS_START_BUILDING")}
      </Typography.H1>
    </div>
  );
}
