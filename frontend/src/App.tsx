import { useForm, Controller } from "react-hook-form";
import axios from "axios";
import { useState } from "react";

export default function Signup() {
  const { register, handleSubmit, control } = useForm();

  const onSubmit = async (data: any) => {
    // interests will be an array — optional: join into a string if your backend expects it
    await axios.post("/api/signup", { data });
    alert("Check your inbox for confirmation!");
  };

  const defaultInterests = [
    "Technology",
    "Health",
    "Finance",
    "Education",
    "Entertainment",
    "Sports",
    "Travel",
    "Food",
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6 w-full">
      <h1 className="text-3xl font-bold mb-10">Say hello to ALAN!</h1>
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="space-y-4 h-full w-1/2 max-w-md"
      >
        <input
          {...register("name")}
          type="text"
          placeholder="Name"
          className="input w-full"
          required
        />
        <input
          {...register("email")}
          type="email"
          placeholder="Email"
          className="input w-full"
          required
        />

        {/* Replace textarea with controlled chip selector */}
        <Controller
          name="interests"
          control={control}
          defaultValue={[]}
          rules={{ validate: (v) => v.length > 0 || "Select at least one" }}
          render={({ field: { value, onChange }, fieldState: { error } }) => (
            <InterestSelector
              defaultInterests={defaultInterests}
              selected={value}
              onChange={onChange}
              error={error}
            />
          )}
        />

        <button type="submit" className="btn btn-primary w-full">
          Sign Up
        </button>
      </form>
    </div>
  );
}

/* 🧩 Interest Selector Component */
function InterestSelector({ defaultInterests, selected, onChange, error }: 
  {defaultInterests: string[], selected: string[], onChange: (v: string[]) => void, error: any}) {
  
  const [interests, setInterests] = useState(defaultInterests);
  const [newInterest, setNewInterest] = useState("");

  const toggleInterest = (interest: string) => {
    const updated = selected.includes(interest)
      ? selected.filter((i: string) => i !== interest)
      : [...selected, interest];
    onChange(updated);
  };

  const addInterest = () => {
    const value = newInterest.trim();
    if (!value) return;
    if (!interests.includes(value)) setInterests([...interests, value]);
    if (!selected.includes(value)) onChange([...selected, value]);
    setNewInterest("");
  };

  return (
    <div>
      <label className="block text-sm font-medium mb-1">
        Select your interests:
      </label>
      <div className="flex flex-wrap gap-2 mb-2">
        {interests.map((interest) => (
          <button
            type="button"
            key={interest}
            onClick={() => toggleInterest(interest)}
            className={`px-3 py-1 rounded-full border transition-all ${
              selected.includes(interest)
                ? "bg-blue-500 text-white border-blue-500"
                : "bg-white text-gray-700 hover:bg-gray-100 border-gray-300"
            }`}
          >
            {interest}
          </button>
        ))}
      </div>

      <div className="flex gap-2 mb-1">
        <input
          type="text"
          placeholder="Add your own..."
          value={newInterest}
          onChange={(e) => setNewInterest(e.target.value)}
              onKeyDown={(e) => {
      if (e.key === "Enter") {
        e.preventDefault(); // Prevent form submission
        addInterest();      // Call your add function
      }
    }}
          className="flex-1 border rounded-full px-3 py-1"
        />
        <button
          type="button"
          onClick={addInterest}
          className="bg-blue-500 text-white rounded-full px-3 py-1"
        >
          Add
        </button>
      </div>

      {error && (
        <p className="text-red-500 text-sm mt-1">{error.message}</p>
      )}
    </div>
  );
}