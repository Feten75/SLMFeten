// Fonction pour créer un compte
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const userData = {
        username: document.getElementById('reg_user').value,
        email: document.getElementById('reg_email').value,
        password: document.getElementById('reg_pass').value,
        role: document.getElementById('reg_role').value
    };

    const response = await fetch('/api/user/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
    });

    if (response.ok) {
        Swal.fire("Succès", "Utilisateur créé !", "success");
        e.target.reset();
    } else {
        Swal.fire("Erreur", "Impossible de créer l'utilisateur", "error");
    }
});

function logout() {
    localStorage.clear();
    window.location.href = "/login";
}
