import { redirect } from "next/navigation";

/** Home is the portfolio now. Old links still work. */
export default function PortfolioRedirect() {
  redirect("/home");
}
