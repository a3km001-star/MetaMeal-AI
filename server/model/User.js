const mongoose = require("mongoose");

const Users = new mongoose.Schema({
  name: String,
  email: String,
  password: String,
  age: String,
  height: String,
  weight: String,
  workoutExperience: String,
  dietPreference: String,
  goal: String,
  activityLevel: String,
});

const UserModel = mongoose.model("UserData", Users);
module.exports = UserModel;
