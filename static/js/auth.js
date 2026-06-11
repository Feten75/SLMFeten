document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const loginData = {
        username: document.getElementById('username').value,
        password: document.getElementById('password').value
    };

    try {
        const response = await fetch('/api/user/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(loginData)
        });

        const data = await response.json();

        if (response.ok) {
            // Stockage identique à ce que vous faisiez en Angular
            localStorage.setItem("token", data.accessToken);
            localStorage.setItem("role", data.role);
            localStorage.setItem("username", data.username);

            // Redirection selon le rôle
            if (data.role === "ADMIN") {
                window.location.href = "/admin";
            } else {
                window.location.href = "/chat";
            }
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Erreur',
                text: data.detail || 'Identifiants invalides'
            });
        }
    } catch (err) {
        console.error("Erreur connexion", err);
    }
});
