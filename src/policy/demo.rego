package demo

# Simple demo policy
allow = true {
    input.user == "admin"
}

allow = false {
    input.user != "admin"
}

# Hello world policy
greeting(user) = "Hello, " + user.name {
    user.greeting == true
}

greeting(user) = "Welcome" {
    not user.greeting
}