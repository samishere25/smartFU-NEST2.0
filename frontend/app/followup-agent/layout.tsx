import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'SmartFU - Follow-Up',
  description: 'Patient safety follow-up',
};

export default function FollowUpAgentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
