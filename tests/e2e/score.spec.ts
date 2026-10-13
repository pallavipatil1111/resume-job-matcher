import { test, expect } from "@playwright/test";
import { readFileSync } from "fs";
import path from "path";

const fixtures = path.join(__dirname, "..", "fixtures");
const JOB = readFileSync(path.join(fixtures, "job_java_backend.txt"), "utf-8");

test.beforeEach(async ({ page }) => {
  await page.goto("/");
});

test("scores an uploaded PDF against a job description", async ({ page }) => {
  await page.locator("#resume-file").setInputFiles(path.join(fixtures, "sample_resume.pdf"));
  await expect(page.locator("#file-label")).toHaveText("sample_resume.pdf");
  await page.getByRole("textbox", { name: "Job description" }).fill(JOB);
  await page.getByRole("button", { name: "Score my resume" }).click();

  await expect(page.locator("#results")).toBeVisible();
  const score = Number(await page.locator("#score").textContent());
  expect(score).toBeGreaterThan(0);
  expect(score).toBeLessThanOrEqual(100);
  await expect(page.locator("#missing-skills")).toContainText("Docker");
  await expect(page.locator("#matched-skills")).toContainText("Spring Boot");
  await expect(page.locator("#suggestions li").first()).toBeVisible();
});

test("scores pasted resume text", async ({ page }) => {
  await page.getByRole("tab", { name: "Paste text" }).click();
  await page.getByRole("textbox", { name: "Resume text" }).fill(
    "Java developer building REST APIs with Spring Boot and MySQL. Unit tests with JUnit and Mockito. Docker and Git. " .repeat(3),
  );
  await page.getByRole("textbox", { name: "Job description" }).fill(JOB);
  await page.getByRole("button", { name: "Score my resume" }).click();
  await expect(page.locator("#verdict")).not.toBeEmpty();
  await expect(page.locator("#matched-skills")).toContainText("Docker");
});

test("explains what is missing before submitting", async ({ page }) => {
  await page.getByRole("button", { name: "Score my resume" }).click();
  await expect(page.getByRole("alert")).toHaveText("Choose your resume PDF, or switch to Paste text.");

  await page.locator("#resume-file").setInputFiles(path.join(fixtures, "sample_resume.pdf"));
  await page.getByRole("button", { name: "Score my resume" }).click();
  await expect(page.getByRole("alert")).toHaveText("Paste the full job description, at least a few sentences.");
  await expect(page.locator("#results")).toBeHidden();
});

test("shows the server's message for a file that isn't a PDF", async ({ page }) => {
  await page.locator("#resume-file").setInputFiles(path.join(fixtures, "not_a_pdf.pdf"));
  await page.getByRole("textbox", { name: "Job description" }).fill(JOB);
  await page.getByRole("button", { name: "Score my resume" }).click();
  await expect(page.getByRole("alert")).toContainText("isn't a PDF");
});
