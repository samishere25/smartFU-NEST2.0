import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'SmartFU - Agentic Follow-Up Orchestration',
  description: 'AI-powered case analysis and decision orchestration system',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
