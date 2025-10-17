import { Tooltip } from "@heroui/react";
import { AgentState } from "#/types/agent-state";

interface ActionButtonProps {
  isDisabled?: boolean;
  content: string;
  action: AgentState;
  handleAction: (action: AgentState) => void;
}

export function ActionButton({
  isDisabled = false,
  content,
  action,
  handleAction,
  children,
}: React.PropsWithChildren<ActionButtonProps>) {
  return (
    <Tooltip content={content} closeDelay={100}>
      <button
        onClick={() => handleAction(action)}
        disabled={isDisabled}
        className="relative overflow-visible cursor-default hover:cursor-pointer group disabled:cursor-not-allowed transition-all duration-300 ease-in-out border border-transparent hover:border-red-400/40 rounded-full p-1 hover:scale-110 active:scale-95 hover:bg-red-500/10"
        type="button"
      >
        <span className="relative group-hover:filter group-hover:drop-shadow-[0_0_8px_rgba(255,64,0,0.6)] transition-all duration-300">
          {children}
        </span>
      </button>
    </Tooltip>
  );
}
