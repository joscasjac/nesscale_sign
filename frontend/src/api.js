export async function api(method, args = {}) {
	const response = await fetch("/api/method/nesscale_sign.api." + method, {
		method: "POST",
		credentials: "same-origin",
		headers: {
			"Content-Type": "application/json",
			"X-Frappe-CSRF-Token": window.csrf_token || "",
		},
		body: JSON.stringify(args),
	});
	let data;
	try {
		data = await response.json();
	} catch {
		throw new Error("The server could not respond. Please try again.");
	}
	if (!response.ok || data.exc) {
		let message = "The request failed. Please try again.";
		try {
			message = JSON.parse(JSON.parse(data._server_messages)[0]).message;
		} catch {
			message = data.message || message;
		}
		// Server errors can include HTML. Render through Vue text interpolation only.
		throw new Error(String(message).replace(/<[^>]+>/g, ""));
	}
	return data.message;
}
export async function upload(file) {
	if (!file || file.size > 15 * 1024 * 1024) throw new Error("Choose a PDF smaller than 15 MB.");
	const body = new FormData();
	body.append("file", file);
	body.append("is_private", "1");
	const r = await fetch("/api/method/upload_file", {
		method: "POST",
		credentials: "same-origin",
		headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
		body,
	});
	const data = await r.json();
	if (!r.ok || !data.message?.file_url) throw new Error("Upload failed. Please try again.");
	return data.message.file_url;
}
export const downloadUrl = (method, args) =>
	"/api/method/nesscale_sign.api." + method + "?" + new URLSearchParams(args);
export function date(value) {
	if (!value) return "—";
	const text = String(value).replace(" ", "T");
	const parsed = new Date(/^\d{4}-\d{2}-\d{2}$/.test(text) ? text + "T00:00:00" : text);
	return Number.isNaN(parsed.getTime())
		? "—"
		: new Intl.DateTimeFormat("en", {
				month: "short",
				day: "numeric",
				year: "numeric",
			}).format(parsed);
}
