import * as React from "react";
import { useSession } from "next-auth/react"

const MenuPage = () => {
  const { data: session, status } = useSession()

  if (!session) {
    return (
    <p>
    <a href="/api/auth/signin">Sign in</a>
    </p>)
  }
 
  return <h1>{session ? `${session.user.name}, `: ''}This is menu page</h1>;
};

export default MenuPage;