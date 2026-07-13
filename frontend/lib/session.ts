import { cookies } from "next/headers";
import { COOKIE_NAME } from "./config";

export function getToken(): string | undefined {
  return cookies().get(COOKIE_NAME)?.value;
}
