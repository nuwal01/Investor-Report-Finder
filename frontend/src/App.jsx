import { Routes, Route, Navigate } from 'react-router-dom'
import { SignedIn, SignedOut, RedirectToSignIn, SignIn, SignUp } from '@clerk/clerk-react'
import LandingPage from './components/LandingPage'
import FinderApp from './FinderApp'

function App() {
    return (
        <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route
                path="/app"
                element={
                    <>
                        <SignedIn>
                            <FinderApp />
                        </SignedIn>
                        <SignedOut>
                            <RedirectToSignIn />
                        </SignedOut>
                    </>
                }
            />
            <Route
                path="/sign-in/*"
                element={<SignIn routing="path" path="/sign-in" />}
            />
            <Route
                path="/sign-up/*"
                element={<SignUp routing="path" path="/sign-up" />}
            />
            {/* Redirect any unknown routes to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    )
}

export default App
