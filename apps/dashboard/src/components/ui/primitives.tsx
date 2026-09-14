import {
  cloneElement,
  isValidElement,
  useId,
  type ButtonHTMLAttributes,
  type DialogHTMLAttributes,
  type HTMLAttributes,
  type LabelHTMLAttributes,
  type ReactElement,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";

type Tone = "neutral" | "brand" | "normal" | "attention" | "near" | "critical" | "unknown";
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md";
type DataStatusValue = "real" | "estimated" | "simulated" | "prepared" | "inconclusive";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon?: ReactNode;
  iconPosition?: "start" | "end";
  loading?: boolean;
  loadingLabel?: string;
  size?: ButtonSize;
  variant?: ButtonVariant;
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  "aria-label": string;
  loading?: boolean;
  loadingLabel?: string;
  variant?: ButtonVariant;
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

interface DataStatusProps extends Omit<BadgeProps, "children" | "tone"> {
  status: DataStatusValue;
}

interface AlertProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  tone?: Exclude<Tone, "brand">;
  title?: ReactNode;
}

interface CardProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  footer?: ReactNode;
  title?: ReactNode;
}

interface EmptyStateProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  action?: ReactNode;
  description?: ReactNode;
  title: ReactNode;
}

interface ErrorStateProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  action?: ReactNode;
  description?: ReactNode;
  title?: ReactNode;
}

interface SkeletonProps extends HTMLAttributes<HTMLSpanElement> {
  label?: string;
}

interface FieldProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  error?: ReactNode;
  hint?: ReactNode;
  htmlFor: string;
  label: ReactNode;
  labelProps?: LabelHTMLAttributes<HTMLLabelElement>;
  required?: boolean;
}

interface SelectOption {
  disabled?: boolean;
  label: string;
  value: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  placeholder?: string;
}

interface TabItem {
  disabled?: boolean;
  href?: string;
  id: string;
  label: ReactNode;
  selected?: boolean;
}

interface TabsProps extends HTMLAttributes<HTMLDivElement> {
  items: TabItem[];
  label: string;
}

interface DialogProps extends Omit<DialogHTMLAttributes<HTMLDialogElement>, "title"> {
  closeLabel?: string;
  footer?: ReactNode;
  title: ReactNode;
}

interface DrawerProps extends DialogProps {
  placement?: "start" | "end" | "bottom";
}

const dataStatusLabels: Record<DataStatusValue, string> = {
  real: "Real",
  estimated: "Estimado",
  simulated: "Simulado",
  prepared: "Preparado",
  inconclusive: "Inconclusivo",
};

function joinClassNames(...names: Array<string | false | null | undefined>): string | undefined {
  const className = names.filter(Boolean).join(" ");
  return className || undefined;
}

export function Button({
  children,
  className,
  disabled,
  icon,
  iconPosition = "start",
  loading = false,
  loadingLabel = "Carregando",
  size = "md",
  type = "button",
  variant = "primary",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <button
      {...props}
      aria-busy={loading || undefined}
      className={joinClassNames("ui-button", `ui-button--${variant}`, `ui-button--${size}`, className)}
      disabled={isDisabled}
      type={type}
    >
      {loading ? <span aria-hidden="true" className="ui-spinner" /> : null}
      {!loading && icon && iconPosition === "start" ? <span aria-hidden="true" className="ui-button__icon">{icon}</span> : null}
      <span>{children}</span>
      {!loading && icon && iconPosition === "end" ? <span aria-hidden="true" className="ui-button__icon">{icon}</span> : null}
      {loading ? <span className="ui-sr-only">{loadingLabel}</span> : null}
    </button>
  );
}

export function IconButton({
  children,
  className,
  disabled,
  loading = false,
  loadingLabel = "Carregando",
  type = "button",
  variant = "secondary",
  ...props
}: IconButtonProps) {
  return (
    <button
      {...props}
      aria-busy={loading || undefined}
      className={joinClassNames("ui-icon-button", `ui-icon-button--${variant}`, className)}
      disabled={disabled || loading}
      type={type}
    >
      {loading ? <span aria-hidden="true" className="ui-spinner" /> : <span aria-hidden="true">{children}</span>}
      {loading ? <span className="ui-sr-only">{loadingLabel}</span> : null}
    </button>
  );
}

export function Badge({ children, className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span {...props} className={joinClassNames("ui-badge", `ui-badge--${tone}`, className)}>
      {children}
    </span>
  );
}

export function DataStatus({ className, status, ...props }: DataStatusProps) {
  return (
    <Badge {...props} className={className} data-status={status} tone={status === "real" ? "normal" : status === "inconclusive" ? "unknown" : "brand"}>
      {dataStatusLabels[status]}
    </Badge>
  );
}

export function Alert({ children, className, role, title, tone = "neutral", ...props }: AlertProps) {
  const alertRole = role ?? (tone === "critical" ? "alert" : "status");
  return (
    <div {...props} className={joinClassNames("ui-alert", `ui-alert--${tone}`, className)} role={alertRole}>
      {title ? <strong>{title}</strong> : null}
      {children ? <div>{children}</div> : null}
    </div>
  );
}

export function Card({ children, className, footer, title, ...props }: CardProps) {
  return (
    <section {...props} className={joinClassNames("ui-card", className)}>
      {title ? <header className="ui-card__header"><h2>{title}</h2></header> : null}
      <div className="ui-card__body">{children}</div>
      {footer ? <footer className="ui-card__footer">{footer}</footer> : null}
    </section>
  );
}

export function EmptyState({ action, className, description, title, ...props }: EmptyStateProps) {
  return (
    <section {...props} className={joinClassNames("ui-empty-state", className)}>
      <h2>{title}</h2>
      {description ? <p>{description}</p> : null}
      {action ? <div className="ui-state-action">{action}</div> : null}
    </section>
  );
}

export function ErrorState({
  action,
  className,
  description = "Nao foi possivel carregar estes dados agora.",
  title = "Algo deu errado",
  ...props
}: ErrorStateProps) {
  return (
    <section {...props} className={joinClassNames("ui-error-state", className)} role="alert">
      <h2>{title}</h2>
      <p>{description}</p>
      {action ? <div className="ui-state-action">{action}</div> : null}
    </section>
  );
}

export function Skeleton({ className, label, ...props }: SkeletonProps) {
  const skeleton = <span {...props} aria-hidden="true" className={joinClassNames("ui-skeleton", className)} />;
  if (!label) return skeleton;
  return (
    <span className="ui-skeleton-wrap">
      {skeleton}
      <span className="ui-sr-only">{label}</span>
    </span>
  );
}

export function Field({
  children,
  className,
  error,
  hint,
  htmlFor,
  label,
  labelProps,
  required = false,
  ...props
}: FieldProps) {
  const hintId = hint ? `${htmlFor}-hint` : undefined;
  const errorId = error ? `${htmlFor}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  const control = isValidElement(children)
    ? cloneElement(children as ReactElement<{ "aria-describedby"?: string; "aria-invalid"?: boolean }>, {
      "aria-describedby": describedBy,
      "aria-invalid": error ? true : undefined,
    })
    : children;

  return (
    <div {...props} className={joinClassNames("ui-field", error ? "ui-field--invalid" : false, className)}>
      <label {...labelProps} htmlFor={htmlFor}>
        {label}
        {required ? <span aria-hidden="true"> *</span> : null}
      </label>
      {hint ? <p id={hintId}>{hint}</p> : null}
      {control}
      {error ? <p className="ui-field__error" id={errorId}>{error}</p> : null}
    </div>
  );
}

export function Select({ className, options, placeholder, ...props }: SelectProps) {
  return (
    <select {...props} className={joinClassNames("ui-select", className)}>
      {placeholder ? <option value="">{placeholder}</option> : null}
      {options.map((option) => (
        <option disabled={option.disabled} key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export function Tabs({ className, items, label, ...props }: TabsProps) {
  return (
    <div {...props} aria-label={label} className={joinClassNames("ui-tabs", className)} role="tablist">
      {items.map((item) => {
        const selected = item.selected ?? false;
        const commonProps = {
          "aria-selected": selected,
          className: "ui-tab",
          id: item.id,
          role: "tab",
          tabIndex: selected ? 0 : -1,
        };
        return item.href ? (
          <a
            {...commonProps}
            aria-disabled={item.disabled || undefined}
            href={item.disabled ? undefined : item.href}
            key={item.id}
          >
            {item.label}
          </a>
        ) : (
          <button {...commonProps} disabled={item.disabled} key={item.id} type="button">
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

export function Dialog({
  children,
  className,
  closeLabel = "Fechar",
  footer,
  title,
  ...props
}: DialogProps) {
  const generatedTitleId = useId();
  const titleId = props["aria-labelledby"] ?? generatedTitleId;
  return (
    <dialog {...props} aria-labelledby={titleId} className={joinClassNames("ui-dialog", className)}>
      <header className="ui-dialog__header">
        <h2 id={titleId}>{title}</h2>
        <form method="dialog">
          <button aria-label={closeLabel} className="ui-icon-button ui-icon-button--ghost" type="submit">x</button>
        </form>
      </header>
      <div className="ui-dialog__body">{children}</div>
      {footer ? <footer className="ui-dialog__footer">{footer}</footer> : null}
    </dialog>
  );
}

export function Drawer({ className, placement = "end", ...props }: DrawerProps) {
  return (
    <Dialog
      {...props}
      className={joinClassNames("ui-drawer", `ui-drawer--${placement}`, className)}
    />
  );
}
