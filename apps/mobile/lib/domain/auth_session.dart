class AuthSession {
  const AuthSession({
    required this.accessToken,
    required this.expiresAt,
    required this.userId,
    required this.email,
    required this.displayName,
  });

  final String accessToken;
  final DateTime expiresAt;
  final String userId;
  final String email;
  final String displayName;

  bool isValidAt(DateTime instant) => expiresAt.isAfter(instant.toUtc());

  Map<String, Object?> toJson() => {
    'access_token': accessToken,
    'expires_at': expiresAt.toUtc().toIso8601String(),
    'user_id': userId,
    'email': email,
    'display_name': displayName,
  };

  factory AuthSession.fromJson(Map<String, Object?> json) => AuthSession(
    accessToken: json['access_token']! as String,
    expiresAt: DateTime.parse(json['expires_at']! as String).toUtc(),
    userId: json['user_id']! as String,
    email: json['email']! as String,
    displayName: json['display_name']! as String,
  );
}
