const express = require("express");
const mongoose = require("mongoose");
const cors = require("cors");
const dotenv = require("dotenv");
const UserModel = require("./model/User");

dotenv.config();

const app = express();
app.use(express.json());
app.use(cors());

mongoose.connect(process.env.MONGODB_URI);

app.post("/register", (req, res) => {
  console.log("Received data:", req.body);
  UserModel.create(req.body)
    .then((user) => {
      console.log("User created:", user);
      res.json(user);
    })
    .catch((err) => {
      console.log("Creation error:", err);
      res.status(400).json(err);
    });
});

app.listen(3001, () => {
  console.log("server is running");
});
