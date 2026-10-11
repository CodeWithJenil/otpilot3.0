import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, CheckCircle, AlertCircle, ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { toast } from "@/components/ui/use-toast";
import LegalLayout from "@/components/LegalLayout";

const feedbackSchema = z.object({
  feedback_type: z.enum(["bug", "feature_request", "improvement", "general"], {
    required_error: "Please select a feedback type",
  }),
  rating: z
    .string()
    .optional()
    .refine((val) => !val || (parseInt(val, 10) >= 1 && parseInt(val, 10) <= 5), {
      message: "Rating must be between 1 and 5",
    }),
  feedback: z
    .string()
    .min(10, "Please provide at least 10 characters")
    .max(5000, "Feedback must be less than 5000 characters"),
  email: z
    .string()
    .email("Please enter a valid email address")
    .max(254, "Email is too long")
    .optional()
    .or(z.literal("")),
  otpilot_version: z.string().max(50, "Version string is too long").optional(),
  operating_system: z.string().max(100, "OS string is too long").optional(),
  python_version: z.string().max(50, "Python version string is too long").optional(),
});

type FeedbackFormData = z.infer<typeof feedbackSchema>;

const FEEDBACK_TYPES = [
  { value: "bug", label: "Bug", description: "Something isn't working correctly" },
  { value: "feature_request", label: "Feature Request", description: "I'd like to suggest a new feature" },
  { value: "improvement", label: "Improvement", description: "An existing feature could be better" },
  { value: "general", label: "General Feedback", description: "Other thoughts or comments" },
];

const RATING_OPTIONS = [
  { value: "5", label: "5 - Excellent" },
  { value: "4", label: "4 - Good" },
  { value: "3", label: "3 - Okay" },
  { value: "2", label: "2 - Poor" },
  { value: "1", label: "1 - Very Poor" },
];

const Feedback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const versionFromUrl = searchParams.get("version") || "";

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
    watch,
    setValue,
  } = useForm<FeedbackFormData>({
    resolver: zodResolver(feedbackSchema),
    defaultValues: {
      feedback_type: "general",
      rating: "",
      feedback: "",
      email: "",
      otpilot_version: versionFromUrl,
      operating_system: "",
      python_version: "",
    },
  });

  const watchedFeedbackType = watch("feedback_type");
  const watchedRating = watch("rating");

  const onSubmit = async (data: FeedbackFormData) => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "Failed to submit feedback");
      }

      setIsSubmitted(true);
      toast({
        title: "Feedback received",
        description: "Thanks for helping improve OTPilot.",
        variant: "default",
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong";
      setSubmitError(message);
      toast({
        title: "Submission failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBackHome = () => {
    navigate("/");
  };

  if (isSubmitted) {
    return (
      <LegalLayout title="Feedback Submitted">
        <div className="mx-auto max-w-xl">
          <div className="text-center py-16">
            <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-500/10">
              <CheckCircle className="h-8 w-8 text-green-500" />
            </div>
            <h1 className="mb-4 text-3xl font-bold tracking-tight">Feedback received</h1>
            <p className="mb-8 text-lg text-muted-foreground font-body leading-relaxed">
              Thanks for helping improve OTPilot.
            </p>
            <Button
              variant="default"
              size="lg"
              onClick={handleBackHome}
              className="gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Button>
          </div>
        </div>
      </LegalLayout>
    );
  }

  return (
    <LegalLayout title="Feedback">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-10 text-center">
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight">Feedback</h1>
          <p className="mt-4 text-lg text-muted-foreground font-body leading-relaxed max-w-xl mx-auto">
            Your feedback helps shape OTPilot.
          </p>
        </div>

        {/* Intro */}
        <div className="mb-8 rounded-lg border border-primary/20 bg-primary/5 p-4 text-sm text-muted-foreground font-body">
          <p className="font-mono text-primary text-sm mb-2">What you can report:</p>
          <ul className="list-disc list-inside space-y-1 font-mono text-xs">
            <li>Bugs — something isn't working correctly</li>
            <li>Feature requests — new capabilities you'd like to see</li>
            <li>Improvements — existing features that could be better</li>
            <li>General feedback — any other thoughts</li>
          </ul>
        </div>

        {/* Form */}
        <Card>
          <CardHeader>
            <CardTitle>Share your feedback</CardTitle>
            <CardDescription>
              All fields are optional except feedback type and your message.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...register}>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                {/* Feedback Type */}
                <FormField
                  control={register}
                  name="feedback_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Feedback Type <span className="text-destructive">*</span></FormLabel>
                      <FormControl>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <SelectTrigger className={cn(errors.feedback_type && "border-destructive")}>
                            <SelectValue placeholder="Select feedback type" />
                          </SelectTrigger>
                          <SelectContent>
                            {FEEDBACK_TYPES.map((type) => (
                              <SelectItem key={type.value} value={type.value}>
                                <div className="space-y-0.5">
                                  <span className="font-medium">{type.label}</span>
                                  <span className="text-xs text-muted-foreground">{type.description}</span>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Rating */}
                <FormField
                  control={register}
                  name="rating"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Rating (Optional)</FormLabel>
                      <FormDescription>
                        How would you rate your experience with OTPilot?
                      </FormDescription>
                      <FormControl>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <SelectTrigger className={cn(errors.rating && "border-destructive")}>
                            <SelectValue placeholder="Select a rating (1-5)" />
                          </SelectTrigger>
                          <SelectContent>
                            {RATING_OPTIONS.map((option) => (
                              <SelectItem key={option.value} value={option.value}>
                                {option.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Feedback Text */}
                <FormField
                  control={register}
                  name="feedback"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Feedback <span className="text-destructive">*</span></FormLabel>
                      <FormDescription>
                        Describe your experience, the bug, or your idea. Minimum 10 characters.
                      </FormDescription>
                      <FormControl>
                        <Textarea
                          {...field}
                          placeholder="Tell us what you think..."
                          rows={6}
                          className={cn(errors.feedback && "border-destructive")}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Email */}
                <FormField
                  control={register}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Email (Optional)</FormLabel>
                      <FormDescription>
                        Only needed if you'd like a response. We never share or sell your email.
                      </FormDescription>
                      <FormControl>
                        <Input
                          {...field}
                          type="email"
                          placeholder="you@example.com"
                          className={cn(errors.email && "border-destructive")}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Hidden/Pre-filled fields */}
                <FormField
                  control={register}
                  name="otpilot_version"
                  render={({ field }) => (
                    <FormItem className="hidden">
                      <FormControl>
                        <Input {...field} type="hidden" />
                      </FormControl>
                    </FormItem>
                  )}
                />
                <FormField
                  control={register}
                  name="operating_system"
                  render={({ field }) => (
                    <FormItem className="hidden">
                      <FormControl>
                        <Input {...field} type="hidden" />
                      </FormControl>
                    </FormItem>
                  )}
                />
                <FormField
                  control={register}
                  name="python_version"
                  render={({ field }) => (
                    <FormItem className="hidden">
                      <FormControl>
                        <Input {...field} type="hidden" />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Submit Button */}
                <Button
                  type="submit"
                  className="w-full"
                  size="lg"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    "Submit Feedback"
                  )}
                </Button>

                {submitError && (
                  <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
                    <AlertCircle className="mr-2 h-4 w-4 inline-block" />
                    {submitError}
                  </div>
                )}
              </form>
            </Form>
          </CardContent>
        </Card>

        {/* Privacy Note */}
        <div className="mt-8 text-center text-sm text-muted-foreground font-body">
          <p>
            Feedback is stored in the OTPilot Neon database. Telemetry does not need to be enabled to
            submit feedback. OTPilot does not automatically include email contents, OTPs, or
            clipboard data in feedback submissions.
          </p>
        </div>
      </div>
    </LegalLayout>
  );
};

export default Feedback;