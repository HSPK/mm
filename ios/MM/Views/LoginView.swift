import SwiftUI

struct LoginView: View {
    @Environment(AuthStore.self) private var auth

    @State private var username = ""
    @State private var password = ""
    @State private var apiBaseURL = AppConfig.apiBaseURL.absoluteString
    @State private var showAdvanced = false
    @FocusState private var focused: Field?

    private enum Field { case username, password, baseURL }

    var body: some View {
        VStack(spacing: 24) {
            VStack(spacing: 12) {
                Image(systemName: "photo.stack.fill")
                    .font(.system(size: 36))
                    .foregroundStyle(.tint)
                    .padding(16)
                    .background(.tint.opacity(0.15), in: .rect(cornerRadius: 18))
                Text("MM")
                    .font(.largeTitle.weight(.bold))
                Text("Your personal media library")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .padding(.top, 32)

            VStack(spacing: 12) {
                TextField("Username", text: $username)
                    .textContentType(.username)
                    .focused($focused, equals: .username)
                #if os(iOS)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.asciiCapable)
                #endif

                SecureField("Password", text: $password)
                    .textContentType(.password)
                    .focused($focused, equals: .password)
                    .onSubmit { Task { await submit() } }

                if let error = auth.error {
                    Label(error, systemImage: "exclamationmark.triangle.fill")
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                Button {
                    Task { await submit() }
                } label: {
                    HStack {
                        if auth.loading { ProgressView().controlSize(.small) }
                        Text(auth.loading ? "Signing in…" : "Sign in")
                            .frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(auth.loading || username.isEmpty || password.isEmpty)
            }
            .textFieldStyle(.roundedBorder)

            DisclosureGroup("Server", isExpanded: $showAdvanced) {
                TextField("API base URL", text: $apiBaseURL)
                    .textFieldStyle(.roundedBorder)
                    .focused($focused, equals: .baseURL)
                #if os(iOS)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                #endif
                    .onChange(of: apiBaseURL) { _, new in
                        if let url = URL(string: new), url.scheme != nil {
                            AppConfig.setAPIBaseURL(url)
                        }
                    }
            }
            .font(.footnote)
            .foregroundStyle(.secondary)

            Spacer()
        }
        .padding(.horizontal, 24)
        .frame(maxWidth: 380)
        .onAppear { focused = .username }
    }

    private func submit() async {
        if username.isEmpty || password.isEmpty { return }
        await auth.signIn(username: username, password: password)
    }
}

#Preview {
    LoginView()
        .environment(AuthStore())
}
