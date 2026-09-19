import { redirect } from "next/navigation";

export default async function JudgingListRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/company/challenges/${id}?section=judging`);
}
