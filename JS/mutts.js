function check(email, email2){
    if (email.value==email2.value) return true;
    else {
        alert("Email addresses must match!");
        return false;
    }
}