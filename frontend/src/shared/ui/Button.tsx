import type { ButtonHTMLAttributes } from 'react';

const VARIANT_CLASSNAME = {
  primary: 'bg-foreground text-background transition-opacity hover:opacity-90',
  outline: 'border border-foreground transition-colors hover:bg-foreground hover:text-background',
} as const;

type ButtonVariant = keyof typeof VARIANT_CLASSNAME;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export const Button = ({ variant = 'primary', className = '', ...props }: ButtonProps) => {
  return (
    <button
      className={`flex items-center justify-center gap-2 rounded text-sm font-medium ${VARIANT_CLASSNAME[variant]} ${className}`}
      {...props}
    />
  );
};
